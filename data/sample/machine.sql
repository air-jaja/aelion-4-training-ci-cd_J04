-- [PÉDAGOGIE] ============================================================================
-- [PÉDAGOGIE] FICHIER — data/sample/machine.sql
-- [PÉDAGOGIE] MODULE  — M23 — ingestion hétérogène, normalisation et jointure temporelle
-- [PÉDAGOGIE] RÔLE    — Transformer plusieurs formats sources en un contrat tabulaire commun et
-- [PÉDAGOGIE]           fabriquer la cible sans mélange de machines.
-- [PÉDAGOGIE] THÉORIE — la normalisation d'identifiant rend les jointures explicites
-- [PÉDAGOGIE]           • merge_asof rapproche des mesures temporelles dans une tolérance
-- [PÉDAGOGIE]             contrôlée
-- [PÉDAGOGIE]           • la clé machine et l'ordre chronologique empêchent une association
-- [PÉDAGOGIE]             inter-équipements
-- [PÉDAGOGIE] À VOIR  — Contrôler schéma, nombre de lignes perdues, ordre des dates et
-- [PÉDAGOGIE]           distribution de la cible.
-- [PÉDAGOGIE] PIÈGE   — Dans les fichiers SQL, ne jamais ajouter en commentaire un faux tuple
-- [PÉDAGOGIE]           ressemblant aux données chargées.
-- [PÉDAGOGIE] GARDE   — Toutes les lignes marquées [PÉDAGOGIE] sont des commentaires : elles
-- [PÉDAGOGIE]           guident la lecture sans changer l'exécution.
-- [PÉDAGOGIE] ============================================================================

-- InduSense 4.0 - référentiel machines (PostgreSQL)
BEGIN;
-- [PÉDAGOGIE] SCHÉMA — déclare une structure et les invariants portés par la base.
CREATE TABLE IF NOT EXISTS machine (
    machine_code            VARCHAR(16) PRIMARY KEY,
    commissioning_date      DATE NOT NULL,
    max_daily_capacity      INTEGER NOT NULL CHECK (max_daily_capacity > 0),
    model                   VARCHAR(32) NOT NULL,
    production_line         VARCHAR(16) NOT NULL,
    location                VARCHAR(16) NOT NULL,
    criticality             VARCHAR(8)  NOT NULL CHECK (criticality IN ('LOW','MEDIUM','HIGH')),
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Petit index utile pour les jointures / filtrages
-- [PÉDAGOGIE] SCHÉMA — déclare une structure et les invariants portés par la base.
CREATE INDEX IF NOT EXISTS idx_machine_line ON machine(production_line);
-- [PÉDAGOGIE] SCHÉMA — déclare une structure et les invariants portés par la base.
CREATE INDEX IF NOT EXISTS idx_machine_location ON machine(location);
-- [PÉDAGOGIE] CHARGEMENT — ajoute le jeu de données de référence dans un ordre reproductible.
INSERT INTO machine (machine_code, commissioning_date, max_daily_capacity, model, production_line, location, criticality)
VALUES
('MACH-01', '2021-05-12', 770, 'InduPress-X2', 'Ligne-A', 'Atelier-2', 'MEDIUM'),
('MACH-02', '2024-09-07', 800, 'InduPress-X2', 'Ligne-A', 'Atelier-1', 'LOW'),
('MACH-03', '2019-07-23', 1405, 'InduPress-X1', 'Ligne-B', 'Atelier-1', 'HIGH'),
('MACH-04', '2023-01-07', 750, 'InduPress-Z1', 'Ligne-C', 'Atelier-3', 'LOW'),
('MACH-05', '2024-03-11', 1380, 'InduPress-X2', 'Ligne-C', 'Atelier-1', 'HIGH'),
('MACH-06', '2022-01-01', 1351, 'InduPress-X3', 'Ligne-A', 'Atelier-1', 'LOW'),
('MACH-07', '2025-05-25', 1428, 'InduPress-Z1', 'Ligne-A', 'Atelier-3', 'MEDIUM'),
('MACH-08', '2023-10-18', 1158, 'InduPress-X1', 'Ligne-B', 'Atelier-2', 'HIGH'),
('MACH-09', '2023-01-15', 1056, 'InduPress-X2', 'Ligne-B', 'Atelier-3', 'MEDIUM'),
('MACH-10', '2021-04-16', 778, 'InduPress-X3', 'Ligne-A', 'Atelier-3', 'LOW'),
('MACH-11', '2022-09-15', 984, 'InduPress-X2', 'Ligne-B', 'Atelier-1', 'MEDIUM'),
('MACH-12', '2024-02-21', 838, 'InduPress-Z1', 'Ligne-B', 'Atelier-2', 'MEDIUM'),
('MACH-13', '2019-12-30', 907, 'InduPress-X3', 'Ligne-C', 'Atelier-3', 'MEDIUM'),
('MACH-14', '2021-10-21', 1191, 'InduPress-X2', 'Ligne-A', 'Atelier-3', 'LOW'),
('MACH-15', '2022-03-16', 1027, 'InduPress-X2', 'Ligne-A', 'Atelier-3', 'MEDIUM')
ON CONFLICT (machine_code) DO UPDATE SET
commissioning_date = EXCLUDED.commissioning_date,
max_daily_capacity = EXCLUDED.max_daily_capacity,
model = EXCLUDED.model,
production_line = EXCLUDED.production_line,
location = EXCLUDED.location,
criticality = EXCLUDED.criticality,
updated_at = NOW();
COMMIT;
