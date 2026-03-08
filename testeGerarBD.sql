-- 1. CRIAÇÃO DAS TABELAS (Schema baseado no arquivo original)
CREATE TABLE IF NOT EXISTS families (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    invite_token VARCHAR(64),
    created_at DATETIME,
    UNIQUE (invite_token)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role VARCHAR(10),
    family_id INTEGER,
    created_at DATETIME,
    UNIQUE (email),
    FOREIGN KEY (family_id) REFERENCES families (id)
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(80) NOT NULL,
    icon VARCHAR(10),
    color VARCHAR(7),
    family_id INTEGER NOT NULL,
    FOREIGN KEY (family_id) REFERENCES families (id)
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER NOT NULL PRIMARY KEY,
    description VARCHAR(200) NOT NULL,
    amount FLOAT NOT NULL,
    type VARCHAR(10) NOT NULL,
    scope VARCHAR(10),
    date DATE,
    created_at DATETIME,
    user_id INTEGER NOT NULL,
    family_id INTEGER NOT NULL,
    category_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (family_id) REFERENCES families (id),
    FOREIGN KEY (category_id) REFERENCES categories (id)
);

CREATE TABLE IF NOT EXISTS bills (
    id INTEGER NOT NULL PRIMARY KEY,
    description VARCHAR(200) NOT NULL,
    amount FLOAT NOT NULL,
    due_date DATE NOT NULL,
    paid BOOLEAN,
    paid_at DATETIME,
    type VARCHAR(10),
    scope VARCHAR(10),
    user_id INTEGER NOT NULL,
    family_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (family_id) REFERENCES families (id)
);

CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER NOT NULL PRIMARY KEY,
    amount FLOAT NOT NULL,
    month INTEGER NOT NULL,
    year INTEGER NOT NULL,
    scope VARCHAR(10),
    family_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    FOREIGN KEY (family_id) REFERENCES families (id),
    FOREIGN KEY (category_id) REFERENCES categories (id)
);

-- 2. DADOS FIXOS
INSERT INTO
    families (id, name, invite_token, created_at)
VALUES
    (
        1,
        'Família Ferreira',
        'token-2025-simulado',
        '2024-12-31 23:59:59'
    );

INSERT INTO
    users (
        id,
        name,
        email,
        password_hash,
        role,
        family_id,
        created_at
    )
VALUES
    (
        1,
        'Jonatas Ferreira',
        'eletrojpf@gmail.com',
        'scrypt:32768:8:1$hash',
        'admin',
        1,
        '2025-01-01 08:00:00'
    );

INSERT INTO
    categories (id, name, icon, color, family_id)
VALUES
    (1, 'Pagamento', '💰', '#6366f1', 1),
    (2, 'Adiantamento', '💸', '#6366f1', 1),
    (3, 'Vale Alimentacao', '🥗', '#6366f1', 1),
    (4, 'Supermercado', '🛒', '#f97316', 1),
    (5, 'Habitação', '🏠', '#ef4444', 1),
    (6, 'Transporte', '🚗', '#eab308', 1),
    (7, 'Lazer', '🎮', '#a855f7', 1),
    (8, 'Saúde', '💊', '#06b6d4', 1);

-- 3. INSERÇÕES MENSAIS (Receitas e Gastos)
INSERT INTO
    transactions (
        description,
        amount,
        type,
        scope,
        date,
        created_at,
        user_id,
        family_id,
        category_id
    )
WITH RECURSIVE
    months (m) AS (
        SELECT
            1
        UNION ALL
        SELECT
            m + 1
        FROM
            months
        WHERE
            m < 12
    )
SELECT
    'Salário Mensal',
    4500.0,
    'income',
    'personal',
    date('2025-' || printf ('%02d', m) || '-05'),
    datetime ('2025-' || printf ('%02d', m) || '-05 09:00:00'),
    1,
    1,
    1
FROM
    months
UNION ALL
SELECT
    'Adiantamento',
    1500.0,
    'income',
    'personal',
    date('2025-' || printf ('%02d', m) || '-20'),
    datetime ('2025-' || printf ('%02d', m) || '-20 09:00:00'),
    1,
    1,
    2
FROM
    months
UNION ALL
SELECT
    'Vale Alimentação',
    800.0,
    'income',
    'personal',
    date('2025-' || printf ('%02d', m) || '-01'),
    datetime ('2025-' || printf ('%02d', m) || '-01 08:00:00'),
    1,
    1,
    3
FROM
    months
UNION ALL
SELECT
    'Supermercado',
    1150.0,
    'expense',
    'family',
    date('2025-' || printf ('%02d', m) || '-10'),
    datetime ('2025-' || printf ('%02d', m) || '-10 18:00:00'),
    1,
    1,
    4
FROM
    months
UNION ALL
SELECT
    'Uber / Combustível',
    65.0,
    'expense',
    'personal',
    date('2025-' || printf ('%02d', m) || '-15'),
    datetime ('2025-' || printf ('%02d', m) || '-15 18:30:00'),
    1,
    1,
    6
FROM
    months;

-- 4. CONTAS FIXAS (Bills)
INSERT INTO
    bills (
        description,
        amount,
        due_date,
        paid,
        paid_at,
        type,
        scope,
        user_id,
        family_id
    )
WITH RECURSIVE
    months (m) AS (
        SELECT
            1
        UNION ALL
        SELECT
            m + 1
        FROM
            months
        WHERE
            m < 12
    )
SELECT
    'Conta de Luz',
    185.0,
    date('2025-' || printf ('%02d', m) || '-28'),
    1,
    datetime ('2025-' || printf ('%02d', m) || '-27 10:00:00'),
    'payable',
    'family',
    1,
    1
FROM
    months;

-- 5. ORÇAMENTOS (Budgets)
INSERT INTO
    budgets (
        amount,
        month,
        year,
        scope,
        family_id,
        category_id
    )
WITH RECURSIVE
    months (m) AS (
        SELECT
            1
        UNION ALL
        SELECT
            m + 1
        FROM
            months
        WHERE
            m < 12
    )
SELECT
    1500.0,
    m,
    2025,
    'family',
    1,
    4
FROM
    months
UNION ALL
SELECT
    400.0,
    m,
    2025,
    'family',
    1,
    6
FROM
    months;