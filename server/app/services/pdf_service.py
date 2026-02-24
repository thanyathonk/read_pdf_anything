import pdfplumber
import fitz  # PyMuPDF - import name is 'fitz' not 'pymupdf'
import hashlib
import time
import io
import base64
import json
import os
import tempfile
from typing import Dict, List, Optional
from PIL import Image
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings
from app.services.vector_store import vector_store  # Use singleton
from app.services.llm_service import llm_service
from app.services.database import database
from app.services.image_store_service import (
    image_store_service,
)  # InMemoryStore for images
from bson import ObjectId
from datetime import datetime

# Try to import img2table for image-based table extraction
try:
    from img2table.document import PDF as Img2TablePDF

    IMG2TABLE_AVAILABLE = True
except ImportError:
    IMG2TABLE_AVAILABLE = False
    print("Warning: img2table not available. Image-based table extraction disabled.")


class PDFService:
    def __init__(self):
        # Use singleton vector_store instead of creating new instance
        self.vector_store = vector_store
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP
        )
        self.pdf_storage: Dict[str, Dict] = {}
        # Note: image_data_store moved to image_store_service (InMemoryStore)

        # Load existing PDF storage on startup
        self._load_pdf_storage()

    def _get_storage_path(self) -> str:
        """Get path for PDF storage file"""
        return os.path.join(settings.PERSIST_DIRECTORY, "pdf_storage.json")

    def _load_pdf_storage(self):
        """Load PDF storage from file on startup"""
        try:
            storage_path = self._get_storage_path()
            if os.path.exists(storage_path):
                with open(storage_path, "r", encoding="utf-8") as f:
                    self.pdf_storage = json.load(f)
                print(f"Loaded {len(self.pdf_storage)} PDFs from storage")
                # Note: Image stores now use InMemoryStore (loaded on demand)
        except Exception as e:
            print(f"Warning: Failed to load PDF storage: {e}")
            self.pdf_storage = {}

    def _save_pdf_storage(self):
        """Save PDF storage to file"""
        try:
            storage_path = self._get_storage_path()
            os.makedirs(os.path.dirname(storage_path), exist_ok=True)

            with open(storage_path, "w", encoding="utf-8") as f:
                json.dump(self.pdf_storage, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save PDF storage: {e}")

    def image_to_base64(self, pil_image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        buffered = io.BytesIO()
        pil_image.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def _convert_table_to_html(
        self, table_data: List[List], headers: List = None
    ) -> str:
        """Convert table data to HTML table structure for better LLM understanding"""
        try:
            html_parts = ["<table>"]

            # Add header row if available
            if headers and len(headers) > 0:
                html_parts.append("<thead>")
                html_parts.append("<tr>")
                for header in headers:
                    # Clean header text
                    header_text = str(header).strip() if header else ""
                    html_parts.append(f"<th>{header_text}</th>")
                html_parts.append("</tr>")
                html_parts.append("</thead>")

            # Add body rows
            html_parts.append("<tbody>")

            # Determine start index (skip header if it's in table_data)
            start_idx = (
                1 if headers and len(table_data) > 0 and table_data[0] == headers else 0
            )

            for row in table_data[start_idx:]:
                if not row or len(row) == 0:
                    continue

                html_parts.append("<tr>")
                for cell in row:
                    # Clean cell text
                    cell_text = str(cell).strip() if cell is not None else ""
                    # Escape HTML special characters
                    cell_text = (
                        cell_text.replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                    )
                    html_parts.append(f"<td>{cell_text}</td>")
                html_parts.append("</tr>")

            html_parts.append("</tbody>")
            html_parts.append("</table>")

            return "\n".join(html_parts)

        except Exception as e:
            print(f"Error converting table to HTML: {e}")
            # Fallback to simple text representation
            return "\n".join(
                [" | ".join(str(cell) for cell in row) for row in table_data]
            )

    async def process_pdf(
        self, pdf_bytes: bytes, filename: str, user_id: Optional[str] = None
    ) -> Dict:
        """Process PDF: extract text, tables, and images"""

        # Choose extraction method based on settings
        if settings.USE_UNSTRUCTURED:
            return await self._process_pdf_with_unstructured(
                pdf_bytes, filename, user_id
            )
        else:
            return await self._process_pdf_legacy(pdf_bytes, filename, user_id)

    def _chunk_html_table(self, html_content: str, max_size: int = 1500) -> List[str]:
        """
        Chunk large HTML tables by rows to avoid embedding overhead.

        Strategy: Split by <tr> tags, keep header row in each chunk.
        """
        import re

        # Extract header row (first <tr>...</tr>)
        header_match = re.search(
            r"<tr[^>]*>.*?</tr>", html_content, re.DOTALL | re.IGNORECASE
        )
        header_row = header_match.group(0) if header_match else ""

        # Extract all rows
        rows = re.findall(r"<tr[^>]*>.*?</tr>", html_content, re.DOTALL | re.IGNORECASE)

        if not rows or len(rows) <= 1:
            # No rows or only header, return as is
            return [html_content]

        chunks = []
        current_chunk = header_row  # Start with header

        for row in rows[1:]:  # Skip first row (already in header)
            # Check if adding this row would exceed max_size
            if len(current_chunk) + len(row) > max_size and current_chunk != header_row:
                # Save current chunk and start new one
                chunks.append(f"<table>{current_chunk}</table>")
                current_chunk = header_row + row
            else:
                current_chunk += row

        # Add last chunk
        if current_chunk:
            chunks.append(f"<table>{current_chunk}</table>")

        return chunks if chunks else [html_content]

    async def _process_pdf_with_unstructured(
        self, pdf_bytes: bytes, filename: str, user_id: Optional[str] = None
    ) -> Dict:
        """Process PDF using unstructured library (NEW METHOD with optimizations)"""
        try:
            from app.services.unstructured_pdf_service import unstructured_pdf_service

            t_total = time.perf_counter()

            # Generate PDF ID
            pdf_id = f"pdf-{int(time.time() * 1000)}-{hashlib.md5(pdf_bytes[:100]).hexdigest()[:8]}"

            # Extract elements with unstructured
            t1 = time.perf_counter()
            extracted = await unstructured_pdf_service.extract_pdf_elements(
                pdf_bytes, filename
            )
            t1_elapsed = time.perf_counter() - t1
            print(f"[Timing] Extract: {t1_elapsed:.2f}s")

            texts = extracted["texts"]
            tables = extracted["tables"]
            images_base64 = extracted["images_base64"]

            # Generate image captions using vision model
            t2 = time.perf_counter()
            image_captions = await unstructured_pdf_service.generate_image_captions(
                images_base64, llm_service
            )
            t2_elapsed = time.perf_counter() - t2
            print(f"[Timing] Captions: {t2_elapsed:.2f}s")

            # Create LangChain documents
            all_docs = []
            image_data_store = {}

            # Add text documents
            for text_item in texts:
                doc = Document(
                    page_content=text_item["content"],
                    metadata={
                        "page": text_item["page"],
                        "type": "text",
                        "element_id": text_item["element_id"],
                        "pdf_id": pdf_id,
                    },
                )
                all_docs.append(doc)

            # Add table documents with smart chunking
            for table_item in tables:
                table_content = table_item["content"]

                # For large HTML tables, split by rows to avoid embedding overhead
                if len(table_content) > 2000 and "<tr>" in table_content:
                    # Split table by rows and create chunks
                    table_chunks = self._chunk_html_table(table_content, max_size=1500)
                    for i, chunk in enumerate(table_chunks):
                        doc = Document(
                            page_content=chunk,
                            metadata={
                                "page": table_item["page"],
                                "type": "table",
                                "element_id": f"{table_item['element_id']}_chunk_{i}",
                                "pdf_id": pdf_id,
                            },
                        )
                        all_docs.append(doc)
                else:
                    # Small table, keep as single document
                    doc = Document(
                        page_content=table_content,
                        metadata={
                            "page": table_item["page"],
                            "type": "table",
                            "element_id": table_item["element_id"],
                            "pdf_id": pdf_id,
                        },
                    )
                    all_docs.append(doc)

            # Add image caption documents (for similarity search)
            for caption_item in image_captions:
                doc = Document(
                    page_content=caption_item["content"],
                    metadata={
                        "page": caption_item["page"],
                        "type": "image_caption",
                        "element_id": caption_item["element_id"],
                        "pdf_id": pdf_id,
                    },
                )
                all_docs.append(doc)

            # Store base64 images in InMemoryStore (for vision retrieval)
            if images_base64:
                image_store_service.add_images(pdf_id, images_base64)

            # Statistics
            text_count = len(texts)
            table_count = len(tables)
            image_count = len(images_base64)

            print(f"[Unstructured] Total documents: {len(all_docs)}")
            print(f"  - Text: {text_count}")
            print(f"  - Tables: {table_count}")
            print(f"  - Image Captions: {len(image_captions)}")
            print(f"  - Base64 Images: {image_count}")

            # Store in vector store
            if user_id:
                persist_dir = os.path.join(
                    settings.PERSIST_DIRECTORY, f"user_{user_id}", pdf_id
                )
            else:
                persist_dir = os.path.join(settings.PERSIST_DIRECTORY, "guest", pdf_id)

            t3 = time.perf_counter()
            self.vector_store.add_documents(
                pdf_id, all_docs, persist_dir, user_id=user_id
            )
            t3_elapsed = time.perf_counter() - t3
            print(f"[Timing] Vector store (embeddings): {t3_elapsed:.2f}s")

            # Store metadata
            pdf_data = {
                "id": pdf_id,
                "filename": filename,
                "size": len(pdf_bytes),
                "chunkCount": len(all_docs),
                "textCount": text_count,
                "tableCount": table_count,
                "imageCount": image_count,
                "uploadedAt": int(time.time() * 1000),
                "user_id": user_id,
            }

            # Store metadata based on user type
            t4 = time.perf_counter()
            if user_id and database.is_connected:
                try:
                    await database.pdfs.insert_one(
                        {
                            "_id": pdf_id,
                            "user_id": ObjectId(user_id),
                            "filename": filename,
                            "size": len(pdf_bytes),
                            "chunkCount": len(all_docs),
                            "textCount": text_count,
                            "tableCount": table_count,
                            "imageCount": image_count,
                            "uploadedAt": datetime.utcnow(),
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                        }
                    )
                    t4_elapsed = time.perf_counter() - t4
                    print(f"[Timing] MongoDB: {t4_elapsed:.2f}s")
                    print(f"PDF metadata stored in MongoDB for user {user_id}")
                except Exception as e:
                    print(f"Warning: Failed to store PDF in MongoDB: {e}")
            else:
                print(
                    f"Guest PDF uploaded: {pdf_id} (metadata stored in browser localStorage)"
                )

            t_total_elapsed = time.perf_counter() - t_total
            print(
                f"[Timing] === PDF processing total: {t_total_elapsed:.2f}s (Extract: {t1_elapsed:.2f}s, Captions: {t2_elapsed:.2f}s, VectorStore: {t3_elapsed:.2f}s) ==="
            )

            # Note: Images already stored in InMemoryStore by image_store_service

            return pdf_data

        except Exception as e:
            raise Exception(f"Unstructured PDF processing failed: {str(e)}")

    async def _process_pdf_legacy(
        self, pdf_bytes: bytes, filename: str, user_id: Optional[str] = None
    ) -> Dict:
        """Process PDF using legacy method (pdfplumber + PyMuPDF)"""
        try:
            # Generate PDF ID
            pdf_id = f"pdf-{int(time.time() * 1000)}-{hashlib.md5(pdf_bytes[:100]).hexdigest()[:8]}"

            all_docs = []
            image_data_store = {}

            # Open PDF with both libraries
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            doc_plumber = pdfplumber.open(io.BytesIO(pdf_bytes))

            print(f"Processing PDF: {filename}")

            for i, page in enumerate(doc):
                page_num = i + 1
                print(f"Processing Page {page_num}")

                # 1. TEXT EXTRACTION
                text = page.get_text()
                if text.strip():
                    temp_doc = Document(
                        page_content=text,
                        metadata={"page": page_num, "type": "text", "pdf_id": pdf_id},
                    )
                    text_chunks = self.splitter.split_documents([temp_doc])
                    all_docs.extend(text_chunks)
                    print(f"   Extracted {len(text_chunks)} text chunks")

                # 2. TABLE EXTRACTION (Simplified and Robust)
                try:
                    extracted_table_data = []  # Store all extracted tables as raw data

                    # ==== PRIMARY METHOD: PyMuPDF find_tables() ====
                    # PyMuPDF 1.23+ has excellent table detection that works with many formats
                    try:
                        pymupdf_tables = page.find_tables()
                        if pymupdf_tables and len(pymupdf_tables.tables) > 0:
                            for tab in pymupdf_tables.tables:
                                try:
                                    table_data = tab.extract()
                                    if table_data and len(table_data) >= 2:
                                        extracted_table_data.append(table_data)
                                except Exception as te:
                                    pass
                            if extracted_table_data:
                                print(
                                    f"   Found {len(extracted_table_data)} tables using PyMuPDF"
                                )
                    except AttributeError:
                        print(
                            "   PyMuPDF find_tables() not available (requires PyMuPDF >= 1.23)"
                        )
                    except Exception as e:
                        print(f"   PyMuPDF find_tables() error: {e}")

                    # ==== FALLBACK: pdfplumber ====
                    if not extracted_table_data:
                        try:
                            plumber_page = doc_plumber.pages[i]

                            # Try lines strategy first
                            found_tables = plumber_page.find_tables(
                                table_settings={
                                    "vertical_strategy": "lines",
                                    "horizontal_strategy": "lines",
                                    "snap_tolerance": 5,
                                    "join_tolerance": 5,
                                }
                            )

                            if found_tables:
                                for tab in found_tables:
                                    try:
                                        data = tab.extract()
                                        if data and len(data) >= 2:
                                            extracted_table_data.append(data)
                                    except Exception:
                                        pass
                                if extracted_table_data:
                                    print(
                                        f"   Found {len(extracted_table_data)} tables using pdfplumber"
                                    )
                        except Exception as e:
                            print(f"   pdfplumber table extraction error: {e}")

                    # ==== VALIDATE AND PROCESS TABLES ====
                    if extracted_table_data:
                        valid_tables = []
                        seen_signatures = set()

                        for table_data in extracted_table_data:
                            # Basic validation
                            if not table_data or len(table_data) < 2:
                                continue

                            num_rows = len(table_data)
                            num_cols = len(table_data[0]) if table_data[0] else 0

                            # Skip if too few columns
                            if num_cols < 2:
                                continue

                            # Skip if too many rows (likely misdetected text)
                            if num_rows > 50:
                                print(f"      Skipped: too many rows ({num_rows})")
                                continue

                            # Count non-empty cells
                            non_empty = sum(
                                sum(1 for c in row if c and str(c).strip())
                                for row in table_data
                                if isinstance(row, list)
                            )

                            # Skip if too few cells
                            if non_empty < 6:
                                continue

                            # Check average cell length (avoid misdetected text paragraphs)
                            total_len = sum(
                                len(str(c).strip())
                                for row in table_data
                                if isinstance(row, list)
                                for c in row
                                if c and str(c).strip()
                            )
                            avg_len = total_len / non_empty if non_empty > 0 else 0

                            if avg_len > 80:
                                print(
                                    f"      Skipped: avg cell too long ({avg_len:.0f} chars)"
                                )
                                continue

                            # Deduplicate using signature
                            sig = str(
                                [
                                    [str(c).strip()[:20] if c else "" for c in row]
                                    for row in table_data[:5]
                                ]
                            )
                            if sig in seen_signatures:
                                continue
                            seen_signatures.add(sig)

                            valid_tables.append(table_data)

                        # Create documents for valid tables
                        for idx, table_data in enumerate(valid_tables):
                            html_table = self._convert_table_to_html(table_data, None)
                            table_doc = Document(
                                page_content=f"Table {idx + 1} on Page {page_num}:\n{html_table}",
                                metadata={
                                    "page": page_num,
                                    "type": "table",
                                    "table_index": idx,
                                    "pdf_id": pdf_id,
                                    "rows": len(table_data),
                                    "cols": len(table_data[0]) if table_data else 0,
                                },
                            )
                            all_docs.append(table_doc)
                            print(
                                f"   Created table: {len(table_data)} rows x {len(table_data[0]) if table_data else 0} cols"
                            )

                        if valid_tables:
                            print(
                                f"   Total tables on page {page_num}: {len(valid_tables)}"
                            )
                    else:
                        print(f"   No tables found on page {page_num}")

                except Exception as e:
                    print(f"   Error extracting tables: {e}")

                # 3. IMAGE EXTRACTION AND CAPTIONING
                images = page.get_images(full=True)
                print(f"   Found {len(images)} images")

                for img_index, img in enumerate(images):
                    try:
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]

                        # Convert to PIL Image
                        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

                        # Skip very small images (likely icons)
                        if pil_image.width < 50 or pil_image.height < 50:
                            print(
                                f"   Skipping small image {img_index} ({pil_image.width}x{pil_image.height})"
                            )
                            continue

                        # Convert to base64
                        img_base64 = self.image_to_base64(pil_image)

                        image_id = f"page_{page_num}_img_{img_index}"
                        image_data_store[image_id] = img_base64

                        print(f"   Generating caption for {image_id}...")

                        # Generate caption using Groq Vision
                        try:
                            caption = await llm_service.generate_image_caption(
                                img_base64, settings.IMAGE_PROMPT_TEMPLATE
                            )
                            print(f"   Caption: {caption[:50]}...")
                        except Exception as caption_error:
                            print(
                                f"   Warning: Failed to generate caption: {caption_error}"
                            )
                            caption = "Image content could not be analyzed"

                        # Create document
                        final_content = f"Image ID: {image_id}\nDescription: {caption}"

                        image_doc = Document(
                            page_content=final_content,
                            metadata={
                                "page": page_num,
                                "type": "image",
                                "image_id": image_id,
                                "pdf_id": pdf_id,
                            },
                        )
                        all_docs.append(image_doc)

                    except Exception as e:
                        print(f"   Error processing image {img_index}: {e}")
                        continue

            # Close documents
            doc.close()
            doc_plumber.close()

            # ==== FALLBACK: img2table for image-based tables ====
            # If no tables found, try img2table which can detect tables embedded as images
            table_count_before_img2table = sum(
                1 for d in all_docs if d.metadata.get("type") == "table"
            )

            if table_count_before_img2table == 0 and IMG2TABLE_AVAILABLE:
                print(
                    "   No structured tables found. Trying img2table for image-based tables..."
                )
                try:
                    # Save PDF bytes to temp file (img2table requires file path)
                    with tempfile.NamedTemporaryFile(
                        suffix=".pdf", delete=False
                    ) as tmp_file:
                        tmp_file.write(pdf_bytes)
                        tmp_path = tmp_file.name

                    try:
                        # Use img2table with implicit rows and borderless detection
                        img2table_pdf = Img2TablePDF(src=tmp_path)
                        img2table_results = img2table_pdf.extract_tables(
                            implicit_rows=True, borderless_tables=True
                        )

                        img2table_count = 0
                        for page_num, page_tables in img2table_results.items():
                            if page_tables:
                                for tab_idx, table in enumerate(page_tables):
                                    try:
                                        df = table.df
                                        # Convert DataFrame to list of lists
                                        table_data = [
                                            df.columns.tolist()
                                        ] + df.values.tolist()

                                        # Basic validation
                                        if (
                                            len(table_data) >= 2
                                            and len(table_data[0]) >= 2
                                        ):
                                            html_table = self._convert_table_to_html(
                                                table_data, None
                                            )
                                            table_doc = Document(
                                                page_content=f"Table {img2table_count + 1} on Page {page_num + 1}:\n{html_table}",
                                                metadata={
                                                    "page": page_num + 1,
                                                    "type": "table",
                                                    "table_index": tab_idx,
                                                    "pdf_id": pdf_id,
                                                    "rows": len(table_data),
                                                    "cols": len(table_data[0])
                                                    if table_data
                                                    else 0,
                                                    "source": "img2table",
                                                },
                                            )
                                            all_docs.append(table_doc)
                                            img2table_count += 1
                                            print(
                                                f"   [img2table] Found table on page {page_num + 1}: {len(table_data)} rows x {len(table_data[0])} cols"
                                            )
                                    except Exception as tab_error:
                                        print(
                                            f"   [img2table] Error processing table: {tab_error}"
                                        )

                        if img2table_count > 0:
                            print(
                                f"   [img2table] Total tables extracted: {img2table_count}"
                            )
                        else:
                            print("   [img2table] No tables found in images")
                    finally:
                        # Clean up temp file
                        try:
                            os.unlink(tmp_path)
                        except Exception:
                            pass

                except Exception as img2table_error:
                    print(f"   [img2table] Error: {img2table_error}")

            # Statistics
            text_count = sum(1 for d in all_docs if d.metadata.get("type") == "text")
            table_count = sum(1 for d in all_docs if d.metadata.get("type") == "table")
            image_count = sum(1 for d in all_docs if d.metadata.get("type") == "image")

            print(f"SUMMARY: {len(all_docs)} total documents")
            print(
                f" - Text: {text_count}, Tables: {table_count}, Images: {image_count}"
            )

            # Store in vector store (path includes user_id if authenticated)
            if user_id:
                # For logged-in users: store in user-specific directory
                persist_dir = os.path.join(
                    settings.PERSIST_DIRECTORY, f"user_{user_id}", pdf_id
                )
            else:
                # For guest users: store in guest directory
                persist_dir = os.path.join(settings.PERSIST_DIRECTORY, "guest", pdf_id)

            self.vector_store.add_documents(
                pdf_id, all_docs, persist_dir, user_id=user_id
            )

            # Store metadata
            pdf_data = {
                "id": pdf_id,
                "filename": filename,
                "size": len(pdf_bytes),
                "chunkCount": len(all_docs),
                "textCount": text_count,
                "tableCount": table_count,
                "imageCount": image_count,
                "uploadedAt": int(time.time() * 1000),
                "user_id": user_id,  # None for guest users
            }

            # Store metadata based on user type
            if user_id and database.is_connected:
                # Store in MongoDB for logged-in users
                try:
                    await database.pdfs.insert_one(
                        {
                            "_id": pdf_id,
                            "user_id": ObjectId(user_id),
                            "filename": filename,
                            "size": len(pdf_bytes),
                            "chunkCount": len(all_docs),
                            "textCount": text_count,
                            "tableCount": table_count,
                            "imageCount": image_count,
                            "uploadedAt": datetime.utcnow(),
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                        }
                    )
                    print(f"PDF metadata stored in MongoDB for user {user_id}")
                except Exception as e:
                    print(f"Warning: Failed to store PDF in MongoDB: {e}")
                    # Fallback: Don't store metadata for logged-in users if MongoDB fails
                    # Frontend will handle this case
            else:
                # Guest users: Don't store metadata in file system
                # Metadata will be stored in browser's localStorage by frontend
                # This prevents server file system from bloating with guest data
                print(
                    f"Guest PDF uploaded: {pdf_id} (metadata should be stored in browser localStorage)"
                )
                # Note: Vector store and image store still need to be in file system
                # but we don't store metadata here to save server space

            # Store image data (always in file system for now)
            self.image_data_store[pdf_id] = image_data_store
            self._save_image_store(pdf_id)

            return pdf_data

        except Exception as e:
            raise Exception(f"PDF processing failed: {str(e)}")

    def _save_image_store(self, pdf_id: str):
        """Save image data store to file"""
        try:
            store_path = os.path.join(
                settings.PERSIST_DIRECTORY, pdf_id, "image_store.json"
            )
            os.makedirs(os.path.dirname(store_path), exist_ok=True)

            if pdf_id in self.image_data_store:
                with open(store_path, "w", encoding="utf-8") as f:
                    json.dump(self.image_data_store[pdf_id], f)
        except Exception as e:
            print(f"Warning: Failed to save image store: {e}")

    def _load_image_store(self, pdf_id: str) -> Dict:
        """Load image data store from file"""
        try:
            store_path = os.path.join(
                settings.PERSIST_DIRECTORY, pdf_id, "image_store.json"
            )
            if os.path.exists(store_path):
                with open(store_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load image store: {e}")
        return {}

    async def get_pdf(
        self, pdf_id: str, user_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Get PDF data by ID - query from MongoDB if logged in, otherwise from file storage"""
        # Try MongoDB first if user is authenticated
        if user_id and database.is_connected:
            try:
                from bson import ObjectId

                pdf_doc = await database.pdfs.find_one(
                    {"_id": pdf_id, "user_id": ObjectId(user_id)}
                )
                if pdf_doc:
                    # Convert MongoDB document to dict format
                    pdf_data = {
                        "id": str(pdf_doc["_id"]),
                        "filename": pdf_doc.get("filename", ""),
                        "size": pdf_doc.get("size", 0),
                        "chunkCount": pdf_doc.get("chunkCount", 0),
                        "textCount": pdf_doc.get("textCount", 0),
                        "tableCount": pdf_doc.get("tableCount", 0),
                        "imageCount": pdf_doc.get("imageCount", 0),
                        "uploadedAt": pdf_doc.get("uploadedAt", None),
                        "user_id": str(pdf_doc.get("user_id", "")),
                    }
                    return pdf_data
            except Exception as e:
                print(f"Warning: Failed to get PDF from MongoDB: {e}")

        # Fallback to file storage (for guest users or if MongoDB fails)
        pdf_data = self.pdf_storage.get(pdf_id)
        if pdf_data:
            return pdf_data

        # For guest users: If not in file storage, check if vector store exists
        # (metadata is in browser localStorage, but vector store is on server)
        if not user_id:
            guest_pdf_dir = os.path.join(settings.PERSIST_DIRECTORY, "guest", pdf_id)
            if os.path.exists(guest_pdf_dir):
                # Return minimal metadata for guest PDFs (metadata is in browser localStorage)
                # We just need to confirm the PDF exists on server
                return {
                    "id": pdf_id,
                    "filename": pdf_id,  # Will be replaced by frontend metadata
                    "size": 0,
                    "chunkCount": 0,
                    "textCount": 0,
                    "tableCount": 0,
                    "imageCount": 0,
                    "uploadedAt": None,
                    "user_id": None,
                }

        return None

    async def get_all_pdfs(self, user_id: Optional[str] = None) -> List[Dict]:
        """Get all PDFs - query from MongoDB if logged in, otherwise from file storage"""
        pdfs = []

        # Try MongoDB first if user is authenticated
        if user_id and database.is_connected:
            try:
                from bson import ObjectId

                # Get PDFs from pdfs collection
                cursor = database.pdfs.find({"user_id": ObjectId(user_id)})
                pdf_ids_in_db = set()
                async for pdf_doc in cursor:
                    pdf_ids_in_db.add(str(pdf_doc["_id"]))
                    # Convert uploadedAt datetime to timestamp (milliseconds)
                    uploaded_at = pdf_doc.get("uploadedAt", None)
                    if uploaded_at:
                        if isinstance(uploaded_at, datetime):
                            uploaded_at = int(uploaded_at.timestamp() * 1000)
                        elif hasattr(uploaded_at, "timestamp"):
                            uploaded_at = int(uploaded_at.timestamp() * 1000)

                    pdf_data = {
                        "id": str(pdf_doc["_id"]),
                        "filename": pdf_doc.get("filename", ""),
                        "size": pdf_doc.get("size", 0),
                        "chunkCount": pdf_doc.get("chunkCount", 0),
                        "textCount": pdf_doc.get("textCount", 0),
                        "tableCount": pdf_doc.get("tableCount", 0),
                        "imageCount": pdf_doc.get("imageCount", 0),
                        "uploadedAt": uploaded_at,
                        "user_id": str(pdf_doc.get("user_id", "")),
                    }
                    pdfs.append(pdf_data)

                # Check pdf_history in user document for PDFs that might not be in pdfs collection yet
                user = await database.users.find_one({"_id": ObjectId(user_id)})
                if user:
                    pdf_history = user.get("pdf_history", [])
                    for pdf_id in pdf_history:
                        if pdf_id not in pdf_ids_in_db:
                            # Try to find PDF in guest storage or file storage
                            # Check if vector store exists (PDF was uploaded as guest)
                            guest_pdf_dir = os.path.join(
                                settings.PERSIST_DIRECTORY, "guest", pdf_id
                            )
                            if os.path.exists(guest_pdf_dir):
                                # PDF exists in guest storage, try to get metadata from file storage
                                pdf_metadata = self.pdf_storage.get(pdf_id)
                                if pdf_metadata:
                                    # Migrate PDF metadata to MongoDB
                                    try:
                                        await database.pdfs.insert_one(
                                            {
                                                "_id": pdf_id,
                                                "user_id": ObjectId(user_id),
                                                "filename": pdf_metadata.get(
                                                    "filename", pdf_id
                                                ),
                                                "size": pdf_metadata.get("size", 0),
                                                "chunkCount": pdf_metadata.get(
                                                    "chunkCount", 0
                                                ),
                                                "textCount": pdf_metadata.get(
                                                    "textCount", 0
                                                ),
                                                "tableCount": pdf_metadata.get(
                                                    "tableCount", 0
                                                ),
                                                "imageCount": pdf_metadata.get(
                                                    "imageCount", 0
                                                ),
                                                "uploadedAt": datetime.utcnow(),
                                                "created_at": datetime.utcnow(),
                                                "updated_at": datetime.utcnow(),
                                            }
                                        )
                                        print(
                                            f"Migrated PDF {pdf_id} to MongoDB for user {user_id}"
                                        )

                                        # Add to pdfs list
                                        uploaded_at = pdf_metadata.get("uploadedAt")
                                        if uploaded_at and isinstance(
                                            uploaded_at, (int, float)
                                        ):
                                            uploaded_at = int(uploaded_at)
                                        elif uploaded_at:
                                            uploaded_at = None

                                        pdfs.append(
                                            {
                                                "id": pdf_id,
                                                "filename": pdf_metadata.get(
                                                    "filename", pdf_id
                                                ),
                                                "size": pdf_metadata.get("size", 0),
                                                "chunkCount": pdf_metadata.get(
                                                    "chunkCount", 0
                                                ),
                                                "textCount": pdf_metadata.get(
                                                    "textCount", 0
                                                ),
                                                "tableCount": pdf_metadata.get(
                                                    "tableCount", 0
                                                ),
                                                "imageCount": pdf_metadata.get(
                                                    "imageCount", 0
                                                ),
                                                "uploadedAt": uploaded_at,
                                                "user_id": user_id,
                                            }
                                        )
                                    except Exception as migrate_error:
                                        print(
                                            f"Warning: Failed to migrate PDF {pdf_id} to MongoDB: {migrate_error}"
                                        )
                                        # Still add to list if metadata exists
                                        uploaded_at = pdf_metadata.get("uploadedAt")
                                        if uploaded_at and isinstance(
                                            uploaded_at, (int, float)
                                        ):
                                            uploaded_at = int(uploaded_at)
                                        elif uploaded_at:
                                            uploaded_at = None

                                        pdfs.append(
                                            {
                                                "id": pdf_id,
                                                "filename": pdf_metadata.get(
                                                    "filename", pdf_id
                                                ),
                                                "size": pdf_metadata.get("size", 0),
                                                "chunkCount": pdf_metadata.get(
                                                    "chunkCount", 0
                                                ),
                                                "textCount": pdf_metadata.get(
                                                    "textCount", 0
                                                ),
                                                "tableCount": pdf_metadata.get(
                                                    "tableCount", 0
                                                ),
                                                "imageCount": pdf_metadata.get(
                                                    "imageCount", 0
                                                ),
                                                "uploadedAt": uploaded_at,
                                                "user_id": user_id,
                                            }
                                        )
                                else:
                                    # PDF exists in guest storage but no metadata in file storage
                                    # Create minimal metadata entry
                                    try:
                                        await database.pdfs.insert_one(
                                            {
                                                "_id": pdf_id,
                                                "user_id": ObjectId(user_id),
                                                "filename": pdf_id,
                                                "size": 0,
                                                "chunkCount": 0,
                                                "textCount": 0,
                                                "tableCount": 0,
                                                "imageCount": 0,
                                                "uploadedAt": datetime.utcnow(),
                                                "created_at": datetime.utcnow(),
                                                "updated_at": datetime.utcnow(),
                                            }
                                        )
                                        print(
                                            f"Created minimal PDF entry {pdf_id} in MongoDB for user {user_id}"
                                        )

                                        pdfs.append(
                                            {
                                                "id": pdf_id,
                                                "filename": pdf_id,
                                                "size": 0,
                                                "chunkCount": 0,
                                                "textCount": 0,
                                                "tableCount": 0,
                                                "imageCount": 0,
                                                "uploadedAt": int(
                                                    datetime.utcnow().timestamp() * 1000
                                                ),
                                                "user_id": user_id,
                                            }
                                        )
                                    except Exception as create_error:
                                        print(
                                            f"Warning: Failed to create PDF entry {pdf_id} in MongoDB: {create_error}"
                                        )

                print(f"Found {len(pdfs)} PDFs for user {user_id} in MongoDB")
                return pdfs
            except Exception as e:
                print(f"Warning: Failed to get PDFs from MongoDB: {e}")

        # Fallback to file storage (for guest users or if MongoDB fails)
        # Filter by user_id if provided (for guest users, user_id is None)
        if user_id:
            return [
                pdf
                for pdf in self.pdf_storage.values()
                if pdf.get("user_id") == user_id
            ]
        else:
            # For guest users, return PDFs without user_id
            return [
                pdf for pdf in self.pdf_storage.values() if pdf.get("user_id") is None
            ]

    async def delete_pdf(self, pdf_id: str, user_id: Optional[str] = None) -> bool:
        """Delete PDF and all associated data"""
        deleted = False

        # Try to delete from MongoDB if user is authenticated
        if user_id and database.is_connected:
            try:
                result = await database.pdfs.delete_one(
                    {"_id": pdf_id, "user_id": ObjectId(user_id)}
                )
                if result.deleted_count > 0:
                    deleted = True
                    print(f"PDF deleted from MongoDB: {pdf_id}")
            except Exception as e:
                print(f"Warning: Failed to delete PDF from MongoDB: {e}")

        # Also try to delete from file storage (for logged-in users with local fallback)
        if pdf_id in self.pdf_storage:
            pdf_data = self.pdf_storage[pdf_id]
            # Only delete if it's a guest PDF or belongs to the user
            if (
                not user_id
                or pdf_data.get("user_id") is None
                or pdf_data.get("user_id") == user_id
            ):
                del self.pdf_storage[pdf_id]
                deleted = True
                print(f"PDF deleted from file storage: {pdf_id}")

        # For guest users: Check if guest directory exists (metadata is in browser localStorage)
        # Even if not in pdf_storage, we should clean up vector store and files
        if not user_id:
            guest_pdf_dir = os.path.join(settings.PERSIST_DIRECTORY, "guest", pdf_id)
            if os.path.exists(guest_pdf_dir):
                deleted = True  # Mark as deleted if guest directory exists
                print(f"Guest PDF directory found: {pdf_id}")

        # Always try to clean up resources if we found something to delete
        if deleted:
            # Remove image store from InMemoryStore
            image_store_service.delete_store(pdf_id)

            # Remove from vector store
            try:
                self.vector_store.remove_documents(pdf_id, user_id=user_id)
                print(f"Vector store removed for: {pdf_id}")
            except Exception as e:
                print(f"Warning: Failed to remove vector store: {e}")

            # Save updated storage
            self._save_pdf_storage()

            # Remove PDF directory (check both user and guest directories)
            import shutil

            # Try user directory first
            if user_id:
                pdf_dir = os.path.join(
                    settings.PERSIST_DIRECTORY, f"user_{user_id}", pdf_id
                )
                if os.path.exists(pdf_dir):
                    try:
                        shutil.rmtree(pdf_dir)
                        print(f"User PDF directory removed: {pdf_dir}")
                    except Exception as e:
                        print(f"Warning: Failed to remove user PDF directory: {e}")

            # Always try guest directory too (for cleanup)
            guest_pdf_dir = os.path.join(settings.PERSIST_DIRECTORY, "guest", pdf_id)
            if os.path.exists(guest_pdf_dir):
                try:
                    shutil.rmtree(guest_pdf_dir)
                    print(f"Guest PDF directory removed: {guest_pdf_dir}")
                except Exception as e:
                    print(f"Warning: Failed to remove guest PDF directory: {e}")

        return deleted

    def get_image_store(self, pdf_id: str) -> Dict:
        """Get image store for PDF (returns dict of element_id -> base64)"""
        return image_store_service.get_all_images(pdf_id)

    async def update_pdf_name(
        self, pdf_id: str, new_filename: str, user_id: Optional[str] = None
    ) -> bool:
        """Update PDF filename (authenticated users only)"""
        try:
            # Only allow authenticated users
            if not user_id:
                return False

            # Update in MongoDB if user is authenticated
            if database.is_connected:
                try:
                    from bson import ObjectId
                    from datetime import datetime

                    result = await database.pdfs.update_one(
                        {"_id": pdf_id, "user_id": ObjectId(user_id)},
                        {
                            "$set": {
                                "filename": new_filename,
                                "updated_at": datetime.utcnow(),
                            }
                        },
                    )
                    if result.modified_count > 0:
                        print(
                            f"Updated PDF name in MongoDB: {pdf_id} -> {new_filename}"
                        )
                        return True
                except Exception as e:
                    print(f"Warning: Failed to update PDF name in MongoDB: {e}")

            return False
        except Exception as e:
            print(f"Error updating PDF name: {e}")
            return False


# Singleton instance
pdf_service = PDFService()
