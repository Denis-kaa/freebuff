from sqlalchemy import text
from app.core.database import engine

def fix_enums():
    enums_to_fix = {
        "userrole": ["CUSTOMER", "EXECUTOR"],
        "orderstatus": ["DRAFT", "OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED", "REVIEW"],
        "offerstatus": ["PENDING", "ACCEPTED", "REJECTED", "WITHDRAWN"],
        "paymenttype": ["FULL", "STAGES"],
        "messagetype": ["OFFER_CREATED", "OFFER_ACCEPTED", "OFFER_REJECTED", "OFFER_WITHDRAWN"]
    }

    tables_to_update = [
        ("users", "role", "userrole"),
        ("orders", "status", "orderstatus"),
        ("offers", "status", "offerstatus"),
        ("offers", "payment_type", "paymenttype"),
        ("messages", "type", "messagetype")
    ]

    with engine.connect() as conn:
        print("🔗 Starting Enum case normalization...")
        
        for enum_type, values in enums_to_fix.items():
            for val in values:
                upper_val = val.upper()
                lower_val = val.lower()
                
                # Check if upper exists
                res = conn.execute(text(
                    "SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid "
                    "WHERE t.typname = :t AND e.enumlabel = :v"
                ), {"t": enum_type, "v": upper_val}).first()
                
                if res:
                    # Check if lower exists
                    res_lower = conn.execute(text(
                        "SELECT 1 FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid "
                        "WHERE t.typname = :t AND e.enumlabel = :v"
                    ), {"t": enum_type, "v": lower_val}).first()
                    
                    if res_lower:
                        print(f"🔄 Both '{upper_val}' and '{lower_val}' exist for {enum_type}. Migrating data...")
                        # Update tables to use lowercase
                        for table, col, t_enum in tables_to_update:
                            if t_enum == enum_type:
                                conn.execute(text(f"UPDATE {table} SET {col} = :lower WHERE {col}::text = :upper"), 
                                             {"lower": lower_val, "upper": upper_val})
                        # We can't easily drop enum values, but at least the data is consistent
                    else:
                        print(f"📝 Renaming label '{upper_val}' -> '{lower_val}' in {enum_type}")
                        try:
                            # Use DDL to rename the value directly
                            conn.execute(text(f"ALTER TYPE {enum_type} RENAME VALUE '{upper_val}' TO '{lower_val}'"))
                        except Exception as e:
                            print(f"⚠️ Failed to rename {upper_val} in {enum_type}: {e}")
        
        conn.commit()
        print("✅ Normalization complete.")

if __name__ == "__main__":
    fix_enums()
