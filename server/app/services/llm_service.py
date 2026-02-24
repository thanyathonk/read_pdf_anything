import asyncio
import logging
from groq import Groq
from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """LLM Service with lazy initialization - allows server to start without GROQ_API_KEY."""

    def __init__(self):
        self._client = None
        self.vision_model = settings.GROQ_VISION_MODEL
        self.synthesis_model = settings.GROQ_SYNTHESIS_MODEL

    @property
    def client(self):
        """Lazy initialization of Groq client."""
        if self._client is None:
            if not settings.GROQ_API_KEY:
                raise ValueError(
                    "GROQ_API_KEY is required for chat. "
                    "Please set GROQ_API_KEY in your .env file."
                )
            self._client = Groq(api_key=settings.GROQ_API_KEY)
            logger.info("Groq client initialized")
        return self._client

    async def generate_image_caption(
        self, image_base64: str, prompt_template: str
    ) -> str:
        """Generate caption for image using Groq"""
        try:
            groq_content = [
                {"type": "text", "text": prompt_template},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}",
                    },
                },
            ]

            chat_completion = await asyncio.to_thread(
                self.client.chat.completions.create,
                messages=[{"role": "user", "content": groq_content}],
                model=self.vision_model,
                max_tokens=1024,
                temperature=0.1,
            )
            return chat_completion.choices[0].message.content.strip()

        except Exception as e:
            raise Exception(f"Failed to generate image caption: {str(e)}")

    async def analyze_image_with_query(self, image_base64: str, user_query: str) -> str:
        """Analyze image with specific query"""
        try:
            chat_completion = await asyncio.to_thread(
                self.client.chat.completions.create,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Look at this image and answer this question specifically: {user_query}",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                },
                            },
                        ],
                    }
                ],
                model=self.vision_model,
                max_tokens=512,
                temperature=0.1,
            )
            return chat_completion.choices[0].message.content.strip()

        except Exception as e:
            raise Exception(f"Failed to analyze image: {str(e)}")

    async def synthesize_answer(self, prompt: str) -> str:
        """Synthesize final answer using synthesis model"""
        try:
            final_response = await asyncio.to_thread(
                self.client.chat.completions.create,
                messages=[{"role": "user", "content": prompt}],
                model=self.synthesis_model,
                temperature=0.1,
            )
            return final_response.choices[0].message.content.strip()

        except Exception as e:
            raise Exception(f"Failed to synthesize answer: {str(e)}")


# Singleton instance
llm_service = LLMService()
