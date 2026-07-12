from app.database.db import SessionLocal, engine, Base
from app.models.models import Cooperative, CooperativeMembership, Farmer

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
    memberships = db.query(CooperativeMembership).filter_by(cooperative_id=coop.id).all()
    if not memberships:
        f1 = Farmer(
            name="Kwame Asante",
            phone="0551234567",
            location="Ashanti",
        )
        db.add(f1)
        db.flush()
        db.add(
            CooperativeMembership(
                farmer_id=f1.id,
                cooperative_id=coop.id,
                crop_type="Cocoa",
                acreage=5.0,
            )
        )
        db.commit()
        print("Created Farmer:", f1.name)
        
    db.close()
    print("Database seeded successfully.")

if __name__ == "__main__":
    seed_db()
