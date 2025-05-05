const { Pool } = require('pg');

// Crée une nouvelle connexion à PostgreSQL
const pool = new Pool({
    user: 'postgres',      
    host: 'localhost',
    database: 'Workflow_Promo',    
    password: '123456', 
    port: 5432,                 
});

module.exports = pool;
