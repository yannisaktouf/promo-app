import os
import subprocess
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

class RcloneHelper:
    def __init__(self):
        self.rclone_path = "C:\\Rclone\\rclone.exe"
        self.config_path = "C:\\Requetes_Quotidiennes\\Rclone\\rclone.conf"
        self.remote = "Prod"
        self.remote_path = "Promo/Retroplanning Promo Yannis.xlsx"
        self.local_temp_dir = "D:\\WinFTP"
        self.local_file_name = "amelioration_continue.xlsx"
        
        # Configuration base de données
        self.db_url = "postgresql://postgres:123456@localhost:5432/Workflow_Promo"  # Remplace par tes informations réelles
        self.table_name = "promos"

        # Mapping des colonnes Excel vers les colonnes DB
        self.column_mapping = {
            "Clôture GAME \nEnvoi Supply" : "date_cloture_game",
            "N°BCP" : "promo_code",
            "FERMETURE ENGAGEMENT niveau magasin": "end_date",
            "OUVERTURE ENGAGEMENT": "start_date",
            "CATALOGUES / COLLECTIONS": "title"
        }

    def download_excel_to_df(self):
        os.makedirs(self.local_temp_dir, exist_ok=True)
        local_file = os.path.join(self.local_temp_dir, self.local_file_name)

        print(f"[INFO] Téléchargement de : {self.remote}:{self.remote_path} → {local_file}")

        result = subprocess.run([
            self.rclone_path,
            "--config", self.config_path,
            "copyto",
            f"{self.remote}:{self.remote_path}",
            local_file
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print("[ERREUR RCLONE]")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            raise RuntimeError("❌ Échec du téléchargement du fichier Excel")

        print(f"[OK] Fichier téléchargé : {local_file}")
        df = pd.read_excel(local_file)
        print(df.columns)
        df.rename(columns=self.column_mapping, inplace=True)
        df = df[pd.to_datetime(df['end_date'], errors='coerce').notna() &
            pd.to_datetime(df['start_date'], errors='coerce').notna() &
            pd.to_datetime(df['date_cloture_game'], errors='coerce').notna()]

        today = datetime.now().date()
        def determine_status(row):
            if pd.to_datetime(row['end_date']).date() < today:
                return "terminé"
            elif pd.to_datetime(row['start_date']).date() > today:
                return "à venir"
            else:
                return "en cours"

        df['status'] = df.apply(determine_status, axis=1)
        df['promo_code'] = df.apply(lambda row: f"{row['Année']}-{row['promo_code']}", axis=1)

        return df[['title', 'start_date', 'end_date', 'status', 'promo_code','date_cloture_game']]

    def export_df_to_db(self, df):
        engine = create_engine(self.db_url)

        with engine.connect() as conn:
            trans = conn.begin()
            try:
                print(f"[INFO] Nettoyage de la table '{self.table_name}' (TRUNCATE)...")
                conn.execute(text(f'TRUNCATE TABLE {self.table_name} RESTART IDENTITY CASCADE;'))

                print(f"[INFO] Insertion des nouvelles données dans '{self.table_name}'...")
                df.to_sql(self.table_name, conn, if_exists='append', index=False)

                trans.commit()
                print(f"[OK] Export réussi vers '{self.table_name}'")
            except Exception as e:
                trans.rollback()
                print("[ERREUR DB]", e)
                raise

# ---- Lancement principal ----

if __name__ == "__main__":
    helper = RcloneHelper()
    df = helper.download_excel_to_df()
    print("\n📄 Aperçu du fichier téléchargé :")
    print(df.head())

    helper.export_df_to_db(df)