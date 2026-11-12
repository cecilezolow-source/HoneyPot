-- HoneyPot Datenbankschema
-- Ausführen mit: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS honeypot CHARACTER SET utf8mb4;
USE honeypot;

-- Wichtig: Client-Verbindung auf UTF-8 (utf8mb4) stellen, BEVOR Daten eingefuegt
-- werden. Sonst werden Umlaute (ä, ö, ü, ß) als Latin-1 interpretiert und doppelt
-- kodiert gespeichert ("FrÃ¼hjahr" statt "Frühjahr").
SET NAMES utf8mb4;

DROP TABLE IF EXISTS honigtopf_details;
DROP TABLE IF EXISTS koenigin_tresor;
DROP TABLE IF EXISTS honigtoepfe;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL   -- absichtlich im Klartext (Demo-Zweck, Verschlüsselung folgt später!)
);

CREATE TABLE honigtoepfe (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    author_id INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (author_id) REFERENCES users(id)
);

-- Beispiel-Imker (Passwörter bewusst im Klartext gespeichert)
INSERT INTO users (username, password) VALUES
    ('admin', 'bienenkoenigin99'),
    ('imker_tom', 'waldhonig2024'),
    ('lisa_b', 'summsumm');

-- Beispiel-Honigtöpfe (Posts)
INSERT INTO honigtoepfe (title, content, author_id) VALUES
    ('Frühjahrshonig ernten', 'Am besten erntet man den Frühjahrshonig Ende Mai, wenn die Rapsblüte vorbei ist. Waben vorsichtig entdeckeln und schleudern.', 2),
    ('Bienenstock winterfest machen', 'Fluglochkeile anbringen, Varroa-Behandlung durchführen und ausreichend Futterreserven (ca. 15-20 kg) sicherstellen.', 3),
    ('Honig-Met selbst ansetzen', 'Honig mit Wasser im Verhältnis 1:4 mischen, Hefe zugeben und bei Zimmertemperatur 4-6 Wochen gären lassen.', 2),
    ('Geheimes Imker-Rezept der Königin', 'Dieser Honigtopf sollte eigentlich nicht für jeden sichtbar sein... (Demo-Datensatz für die Übung)', 1);


-- Sorte (= Farbe des Glases) und Kategorie je Honigtopf.
-- Wird von der App mit einer EIGENEN, parametrisierten Query geladen, damit die
-- Spaltenanzahl der verwundbaren Queries (wichtig für UNION-Übungen) gleich bleibt.
CREATE TABLE honigtopf_details (
    topf_id INT PRIMARY KEY,
    kategorie VARCHAR(30) NOT NULL DEFAULT 'wissen',
    sorte VARCHAR(30) NOT NULL DEFAULT 'bluete',
    FOREIGN KEY (topf_id) REFERENCES honigtoepfe(id) ON DELETE CASCADE
);

INSERT INTO honigtopf_details (topf_id, kategorie, sorte) VALUES
    (1, 'anleitung', 'raps'),
    (2, 'tipp', 'wald'),
    (3, 'rezept', 'bluete'),
    (4, 'rezept', 'heide');

-- ---------------------------------------------------------------------------
-- INSIDER / CTF-ZIEL: Diese Tabelle wird in der App NIRGENDS verwendet.
-- Wer sie findet (z. B. über information_schema.tables) und per UNION ausliest,
-- hat die Flagge erbeutet. Spaltenanzahl passt zur Dashboard-Suche (3 Spalten):
--   %' UNION SELECT id, inhalt, hinweis FROM koenigin_tresor --
-- ---------------------------------------------------------------------------
CREATE TABLE koenigin_tresor (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inhalt VARCHAR(200) NOT NULL,
    hinweis VARCHAR(200) NOT NULL
);

INSERT INTO koenigin_tresor (inhalt, hinweis) VALUES
    ('HONEY{w4chb13n3n_m4ch3n_m1tt4gspau53}', 'Glückwunsch! Du hast den Tresor der Königin geknackt.'),
    ('Das geheime Rezept: 1 Teil Honig, 0 Teile Prepared Statements', 'Und genau deshalb bist du hier reingekommen.');
