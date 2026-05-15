from database.schema import engine, Base
import logging

def reset_database():
    print("⚠️  Iniciando purga de base de datos...")
    # Esto borra TODO en la base de datos conectada (Local o Neon.tech)
    Base.metadata.drop_all(engine)
    print("✅ Tablas eliminadas.")
    
    # Esto las vuelve a crear con la estructura nueva
    Base.metadata.create_all(engine)
    print("✨ Base de datos reconstruida con éxito.")

if __name__ == "__main__":
    confirm = input("¿Estás seguro de que quieres borrar TODOS los datos? (s/n): ")
    if confirm.lower() == 's':
        reset_database()
    else:
        print("Operación cancelada.")

