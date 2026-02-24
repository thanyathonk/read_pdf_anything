import logo from "./logo.svg";
import logo_full from "./logo_full.svg";
import logo_full_dark from "./logo_full_dark.svg";
import search_icon from "./search_icon.svg";
import user_icon from "./user_icon.svg";
import theme_icon from "./theme_icon.svg";
import send_icon from "./send_icon.svg";
import stop_icon from "./stop_icon.svg";
import mountain_img from "./mountain_img.jpg";
import menu_icon from "./menu_icon.svg";
import close_icon from "./close_icon.svg";
import bin_icon from "./bin_icon.svg";
import logout_icon from "./logout_icon.svg";
import diamond_icon from "./diamond_icon.svg";
import gallery_icon from "./gallery_icon.svg";
import rag_diagram from "./rag_diagram.png";

import ai_image1 from "./ai_image1.jpg";
import ai_image2 from "./ai_image2.jpg";
import ai_image3 from "./ai_image3.jpg";
import ai_image4 from "./ai_image4.jpg";
import ai_image5 from "./ai_image5.jpg";
import ai_image6 from "./ai_image6.jpg";
import ai_image7 from "./ai_image7.jpg";
import ai_image8 from "./ai_image8.jpg";
import ai_image9 from "./ai_image9.jpg";
import ai_image10 from "./ai_image10.jpg";
import ai_image11 from "./ai_image11.jpg";
import ai_image12 from "./ai_image12.jpg";

export const assets = {
    logo,
    logo_full,
    search_icon,
    user_icon,
    theme_icon,
    send_icon,
    stop_icon,
    mountain_img,
    menu_icon,
    close_icon,
    bin_icon,
    logout_icon,
    logo_full_dark,
    diamond_icon,
    gallery_icon,
    rag_diagram,
};

export const dummyUserData = {
    "_id": "689c6deed410acddc0d95a0e",
    "name": "GreatStack",
    "email": "admin@example.com",
    "password": "$2b$10$VESVdPDjL5LF.KCU6jKyqeXNSLASAAfpR2kkIJExtMO.PJvZJAudy",
    "credits": 200,
}

// copy for server controllers
export const dummyPlans = [
    {
        _id: "basic",
        name: "Basic",
        price: 10,
        credits: 100,
        features: ['100 text generations', '50 image generations', 'Standard support', 'Access to basic models']
    },
    {
        _id: "pro",
        name: "Pro",
        price: 20,
        credits: 500,
        features: ['500 text generations', '200 image generations', 'Priority support', 'Access to pro models', 'Faster response time']
    },
    {
        _id: "premium",
        name: "Premium",
        price: 30,
        credits: 1000,
        features: ['1000 text generations', '500 image generations', '24/7 VIP support', 'Access to premium models', 'Dedicated account manager']
    }
];


export const dummyPdfFiles = [
    {
        id: "pdf-001-research-paper",
        name: "Research_Paper_2024.pdf",
        size: 2456789,
        uploadedAt: Date.now() - 86400000,
        isSelected: true,
    },
    {
        id: "pdf-002-technical-doc",
        name: "Technical_Documentation.pdf",
        size: 1234567,
        uploadedAt: Date.now() - 172800000,
        isSelected: true,
    },
    {
        id: "pdf-003-guide",
        name: "User_Guide_v2.1.pdf",
        size: 987654,
        uploadedAt: Date.now() - 259200000,
        isSelected: false,
    }
];

export const dummyChatHistory = [
    {
        _id: "chat-001",
        name: "Research Paper Analysis",
        pdfFiles: [
            {
                id: "pdf-001-research-paper",
                name: "Research_Paper_2024.pdf",
                size: 2456789,
                uploadedAt: Date.now() - 86400000,
                isSelected: true,
            }
        ],
        messages: [
            {
                role: "user",
                content: "What is the main topic of this research paper?",
                timestamp: Date.now() - 3600000,
            },
            {
                role: "assistant",
                content: "Based on the research paper, the main topic focuses on **machine learning applications in healthcare**. The paper discusses various approaches to using ML algorithms for medical diagnosis and treatment recommendations.",
                timestamp: Date.now() - 3595000,
            },
            {
                role: "user",
                content: "Can you summarize the methodology section?",
                timestamp: Date.now() - 3000000,
            },
            {
                role: "assistant",
                content: "The methodology section describes a **multi-phase research approach**:\n\n1. **Data Collection**: The study collected medical imaging data from 5 major hospitals over a 2-year period.\n\n2. **Preprocessing**: Images were normalized and standardized using advanced image processing techniques.\n\n3. **Model Training**: Multiple deep learning architectures were tested, including CNNs and Vision Transformers.",
                timestamp: Date.now() - 2995000,
            }
        ],
        createdAt: Date.now() - 86400000,
        updatedAt: Date.now() - 2995000,
    },
    {
        _id: "chat-002",
        name: "Technical Documentation Q&A",
        pdfFiles: [
            {
                id: "pdf-002-technical-doc",
                name: "Technical_Documentation.pdf",
                size: 1234567,
                uploadedAt: Date.now() - 172800000,
                isSelected: true,
            }
        ],
        messages: [
            {
                role: "user",
                content: "What are the key features mentioned in this documentation?",
                timestamp: Date.now() - 7200000,
            },
            {
                role: "assistant",
                content: "According to the technical documentation, the key features include:\n\n1. **API Integration**: RESTful API endpoints with comprehensive authentication\n2. **Real-time Processing**: WebSocket support for live data streaming\n3. **Scalable Architecture**: Microservices-based design supporting horizontal scaling\n4. **Security Features**: End-to-end encryption, OAuth 2.0, and role-based access control",
                timestamp: Date.now() - 7195000,
            }
        ],
        createdAt: Date.now() - 172800000,
        updatedAt: Date.now() - 7195000,
    },
    {
        _id: "chat-003",
        name: "Multi-Document Comparison",
        pdfFiles: [
            {
                id: "pdf-001-research-paper",
                name: "Research_Paper_2024.pdf",
                size: 2456789,
                uploadedAt: Date.now() - 86400000,
                isSelected: true,
            },
            {
                id: "pdf-002-technical-doc",
                name: "Technical_Documentation.pdf",
                size: 1234567,
                uploadedAt: Date.now() - 172800000,
                isSelected: true,
            }
        ],
        messages: [
            {
                role: "user",
                content: "Compare the methodologies used in both documents",
                timestamp: Date.now() - 1800000,
            },
            {
                role: "assistant",
                content: "Comparing the methodologies from both documents:\n\n### **Research Paper Methodology:**\n- **Approach**: Experimental research with controlled variables\n- **Data Collection**: Longitudinal study over 2 years\n- **Analysis**: Statistical analysis using ML algorithms\n\n### **Technical Documentation Methodology:**\n- **Approach**: Implementation-focused with practical examples\n- **Data Collection**: API-based data gathering\n- **Analysis**: Performance benchmarking and scalability testing",
                timestamp: Date.now() - 1795000,
            }
        ],
        createdAt: Date.now() - 259200000,
        updatedAt: Date.now() - 1795000,
    }
];

export const dummyChats = [
    {
        "_id": "689de4bbaa932dc3a8ef6cd7",
        "userId": "689c6deed410acddc0d95a0e",
        "userName": "GreatStack",
        "name": "PDF Chat - Research Paper",
        "pdfFileIds": ["pdf-001-research-paper"],
        "messages": [
            {
                "isImage": false,
                "isPublished": false,
                "role": "user",
                "content": "What is the main topic of this research paper?",
                "timestamp": Date.now() - 3600000,
            },
            {
                "isImage": false,
                "isPublished": false,
                "role": "assistant",
                "content": "Based on the research paper, the main topic focuses on **machine learning applications in healthcare**. The paper discusses various approaches to using ML algorithms for medical diagnosis and treatment recommendations, with particular emphasis on neural networks and their effectiveness in analyzing medical imaging data.\n\nThe research presents findings from a comprehensive study involving multiple healthcare institutions and demonstrates significant improvements in diagnostic accuracy when using ML-assisted systems compared to traditional methods.",
                "timestamp": Date.now() - 3595000,
            },
            {
                "isImage": false,
                "isPublished": false,
                "role": "user",
                "content": "Can you summarize the methodology section?",
                "timestamp": Date.now() - 3000000,
            },
            {
                "isImage": false,
                "isPublished": false,
                "role": "assistant",
                "content": "The methodology section describes a **multi-phase research approach**:\n\n1. **Data Collection**: The study collected medical imaging data from 5 major hospitals over a 2-year period, totaling approximately 50,000 anonymized patient records.\n\n2. **Preprocessing**: Images were normalized and standardized using advanced image processing techniques to ensure consistency across different medical imaging devices.\n\n3. **Model Training**: Multiple deep learning architectures were tested, including:\n   - Convolutional Neural Networks (CNNs)\n   - Vision Transformers (ViT)\n   - Hybrid models combining both approaches\n\n4. **Validation**: The models were validated using a 80/20 train-test split with 5-fold cross-validation to ensure robust results.\n\n5. **Evaluation Metrics**: Performance was measured using accuracy, precision, recall, F1-score, and AUC-ROC metrics.\n\nThe methodology emphasizes ethical considerations, including patient privacy protection and IRB approval for all data usage.",
                "timestamp": Date.now() - 2995000,
            }
        ],
        "createdAt": "2025-08-14T13:29:31.398Z",
        "updatedAt": "2025-08-14T13:29:54.753Z",
    },
    {
        "_id": "689ccb9016a922dd57a23fce",
        "userId": "689c6deed410acddc0d95a0e",
        "userName": "GreatStack",
        "name": "PDF Chat - Technical Documentation",
        "pdfFileIds": ["pdf-002-technical-doc"],
        "messages": [
            {
                "isImage": false,
                "isPublished": false,
                "role": "user",
                "content": "What are the key features mentioned in this documentation?",
                "timestamp": Date.now() - 7200000,
            },
            {
                "isImage": false,
                "isPublished": false,
                "role": "assistant",
                "content": "According to the technical documentation, the key features include:\n\n1. **API Integration**: RESTful API endpoints with comprehensive authentication and authorization mechanisms\n2. **Real-time Processing**: WebSocket support for live data streaming and updates\n3. **Scalable Architecture**: Microservices-based design supporting horizontal scaling\n4. **Security Features**: End-to-end encryption, OAuth 2.0, and role-based access control (RBAC)\n5. **Database Support**: Multi-database compatibility (PostgreSQL, MongoDB, Redis)\n6. **Monitoring & Logging**: Built-in analytics dashboard and comprehensive logging system\n7. **Cloud Deployment**: Support for AWS, Azure, and GCP with containerization via Docker\n\nThe documentation also highlights performance optimizations, including caching strategies and load balancing capabilities.",
                "timestamp": Date.now() - 7195000,
            },
            {
                "isImage": false,
                "isPublished": false,
                "role": "user",
                "content": "How do I implement the authentication system?",
                "timestamp": Date.now() - 6000000,
            },
            {
                "isImage": false,
                "isPublished": false,
                "role": "assistant",
                "content": "Based on the documentation, here's how to implement the authentication system:\n\n### **Step 1: Install Dependencies**\n```bash\nnpm install jsonwebtoken bcryptjs express-validator\n```\n\n### **Step 2: Set Up Environment Variables**\n```env\nJWT_SECRET=your-secret-key\nJWT_EXPIRES_IN=24h\n```\n\n### **Step 3: Create Authentication Middleware**\nThe documentation provides a middleware example that:\n- Validates JWT tokens from the Authorization header\n- Checks user roles and permissions\n- Handles token expiration and refresh\n\n### **Step 4: Implement Login Endpoint**\nThe login process includes:\n1. User credential validation\n2. Password hashing verification using bcrypt\n3. JWT token generation\n4. Token refresh mechanism\n\n### **Step 5: Protect Routes**\nApply the authentication middleware to protected routes:\n```javascript\nrouter.get('/protected', authenticateToken, (req, res) => {\n  // Protected route logic\n});\n```\n\nThe documentation also covers OAuth 2.0 integration for third-party authentication providers.",
                "timestamp": Date.now() - 5995000,
            }
        ],
        "createdAt": "2025-08-13T17:29:52.421Z",
        "updatedAt": "2025-08-14T09:39:19.046Z",
    },
    {
        "_id": "689de4bbaa932dc3a8ef6cd8",
        "userId": "689c6deed410acddc0d95a0e",
        "userName": "GreatStack",
        "name": "PDF Chat - Multiple Documents",
        "pdfFileIds": ["pdf-001-research-paper", "pdf-002-technical-doc"],
        "messages": [
            {
                "isImage": false,
                "isPublished": false,
                "role": "user",
                "content": "Compare the methodologies used in both documents",
                "timestamp": Date.now() - 1800000,
            },
            {
                "isImage": false,
                "isPublished": false,
                "role": "assistant",
                "content": "Comparing the methodologies from both documents:\n\n### **Research Paper Methodology:**\n- **Approach**: Experimental research with controlled variables\n- **Data Collection**: Longitudinal study over 2 years with 50,000+ records\n- **Analysis**: Statistical analysis using ML algorithms\n- **Validation**: 5-fold cross-validation with 80/20 train-test split\n- **Focus**: Healthcare applications with ethical considerations\n\n### **Technical Documentation Methodology:**\n- **Approach**: Implementation-focused with practical examples\n- **Data Collection**: API-based data gathering and real-time processing\n- **Analysis**: Performance benchmarking and scalability testing\n- **Validation**: Unit tests, integration tests, and load testing\n- **Focus**: System architecture and deployment strategies\n\n### **Key Differences:**\n1. **Research Paper**: Academic, research-oriented with statistical rigor\n2. **Technical Doc**: Practical, implementation-focused with code examples\n3. **Research Paper**: Emphasizes reproducibility and peer review\n4. **Technical Doc**: Emphasizes usability and developer experience\n\nBoth methodologies complement each other - the research provides theoretical foundation while the technical doc offers practical implementation guidance.",
                "timestamp": Date.now() - 1795000,
            }
        ],
        "createdAt": "2025-08-13T17:29:52.421Z",
        "updatedAt": "2025-08-14T09:39:19.046Z",
    }
]

export const dummyPublishedImages = [
    {
        "imageUrl": ai_image11,
        "userName": "GreatStack"
    },
    {
        "imageUrl": ai_image10,
        "userName": "GreatStack"
    },
    {
        "imageUrl": ai_image9,
        "userName": "GreatStack"
    },
    {
        "imageUrl": ai_image8,
        "userName": "GreatStack"
    },
    {
        "imageUrl": ai_image7,
        "userName": "GreatStack"
    },
    {
        "imageUrl": ai_image6,
        "userName": "GreatStack"
    },
    {
        "imageUrl": ai_image5,
        "userName": "GreatStack"
    },
    {
        "imageUrl": ai_image4,
        "userName": "GreatStack"
    },
    {
        "imageUrl": ai_image3,
        "userName": "GreatStack"
    },
    {
        "imageUrl": ai_image2,
        "userName": "GreatStack"
    },
    {
        "imageUrl": ai_image1,
        "userName": "GreatStack"
    }
]