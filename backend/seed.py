import uuid
from app.database.db import SessionLocal, engine, Base
from app.models.models import Cooperative, Farmer

def seed_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Check if cooperative exists
    coop = db.query(Cooperative).filter_by(id=1).first()
    if not coop:
        coop = Cooperative(
            name="Ashanti Farmers Co-op",
            description="Test cooperative",
            location="Ashanti",
            currency="GHS"
        )
        db.add(coop)
        db.commit()
        db.refresh(coop)
        print("Created Cooperative ID:", coop.id)
        
    # Check if farmers exist
    farmers = db.query(Farmer).filter_by(cooperative_id=1).all()
    if not farmers:
        f1 = Farmer(
            cooperative_id=1,
            name="Kwame Asante",
            phone="0551234567",
            region="Ashanti",
            crop="Cocoa",
            acreage=5.0
        )
        db.add(f1)
        db.commit()
        print("Created Farmer:", f1.name)
        
    db.close()
    print("Database seeded successfully.")

if __name__ == "__main__":
    seed_db()
