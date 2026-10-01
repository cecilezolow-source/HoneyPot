-- HoneyPot Datenbankschema
-- Ausführen mit: mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS honeypot CHARACTER SET utf8mb4;
USE honeypot;

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
