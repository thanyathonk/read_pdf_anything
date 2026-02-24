from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: Optional[AsyncIOMotorClient] = None
    db = None
    
    async def connect(self):
        """Connect to MongoDB (supports both local and MongoDB Atlas)"""
        try:
            # Build connection URI with database name
            # For MongoDB Atlas: mongodb+srv://user:pass@cluster.mongodb.net/dbname
            # For local: mongodb://localhost:27017/dbname
            
            # Check if using MongoDB Atlas (mongodb+srv://) or local MongoDB
            if settings.MONGODB_URI.startswith('mongodb+srv://'):
                # MongoDB Atlas connection - append database name
                # Format: mongodb+srv://user:pass@cluster.mongodb.net/dbname
                connection_uri = f"{settings.MONGODB_URI}/{settings.MONGODB_DB_NAME}"
            else:
                # Local MongoDB connection - append database name
                # Format: mongodb://localhost:27017/dbname
                connection_uri = f"{settings.MONGODB_URI}/{settings.MONGODB_DB_NAME}"
            
            # Create MongoDB client (Motor supports both local and Atlas)
            self.client = AsyncIOMotorClient(
                connection_uri,
                serverSelectionTimeoutMS=5000
            )
            
            # Get database
            self.db = self.client[settings.MONGODB_DB_NAME]
            
            # Test connection (ping)
            await self.client.admin.command('ping')
            
            # Log successful connection (similar to mongoose 'connected' event)
            logger.info(f"✅ Database connected: {settings.MONGODB_DB_NAME}")
            print(f"✅ Pinged your deployment. You successfully connected to MongoDB!")
            print(f"✅ Database connected: {settings.MONGODB_DB_NAME}")
            
            # Set up connection event listeners (similar to mongoose)
            self._setup_event_listeners()
            
        except Exception as error:
            error_msg = error.message if hasattr(error, 'message') else str(error)
            logger.error(f"❌ Database connection error: {error_msg}")
            print(f"⚠️  MongoDB not available: Running in guest mode (no user authentication)")
            print(f"   Error: {error_msg}")
            print(f"   To enable user login, check your MongoDB connection string in .env")
            # Continue without MongoDB - app still works for anonymous users
            self.client = None
            self.db = None
    
    def _setup_event_listeners(self):
        """Set up MongoDB connection event listeners (similar to mongoose)"""
        if not self.client:
            return
        
        # Note: Motor doesn't have the same event system as mongoose
        # But we can simulate it with connection state checks
        pass
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Database disconnected")
            print("Disconnected from MongoDB")
    
    def get_collection(self, name: str):
        """Get a collection by name"""
        if self.db is None:
            return None
        return self.db[name]
    
    @property
    def users(self):
        """Get users collection"""
        return self.get_collection("users")
    
    @property
    def chat_sessions(self):
        """Get chat sessions collection"""
        return self.get_collection("chat_sessions")
    
    @property
    def pdfs(self):
        """Get PDFs collection"""
        return self.get_collection("pdfs")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to MongoDB"""
        return self.client is not None and self.db is not None

# Singleton instance
database = Database()

async def connect_db():
    """Connect to MongoDB (similar to connectDB function in Node.js)"""
    await database.connect()
    return database

async def get_database():
    """Dependency to get database instance"""
    return database

