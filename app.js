const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const uuidv4 = require('uuid');
const cors = require('cors')
const app = express();

app.use(express.json());
app.use(cors());


// Inicializa o banco SQLite
const db = new sqlite3.Database('machines.db', (err) => {
  if (err) console.error('Erro ao conectar ao SQLite:', err);
  else console.log('Banco de dados SQLite conectado.');
});

// Cria a tabela de máquinas, se não existir
db.run(`
  CREATE TABLE IF NOT EXISTS machines (
    token TEXT PRIMARY KEY,
    tipo TEXT,
    branch TEXT,
    login TEXT,
    senha TEXT,
    lastPing TEXT,
    info TEXT,
    resources TEXT,
    lastCommand TEXT,
    commandTimestamp TEXT, /* Adicionado para controlar o tempo do comando */
    commandResult TEXT,
    message TEXT /* Adicionado para armazenar mensagens enviadas */
  )
`);

db.run(`
  CREATE TABLE IF NOT EXISTS program_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT,
    program_name TEXT,
    window_title TEXT,
    usage_time INTEGER, -- Tempo de uso em segundos
    timestamp TEXT
  )
`);
function saveProgramUsage(token, programName, windowTitle, usageTime) {
  const timestamp = new Date().toISOString();
  
  db.run(
    `INSERT INTO program_usage (token, program_name, window_title, usage_time, timestamp) 
     VALUES (?, ?, ?, ?, ?)`,
    [token, programName, windowTitle, usageTime, timestamp],
    (err) => {
      if (err) console.error('Erro ao salvar uso de programa:', err);
    }
  );
}


// Função para salvar uma máquina no banco de dados
function saveMachine(token, machine) {
  const {
    tipo,
    branch,
    login,
    senha,
    lastPing,
    info,
    resources,
    lastCommand,
    commandTimestamp,
    commandResult,
    message
  } = machine;

  db.run(
    `INSERT OR REPLACE INTO machines 
      (token, tipo, branch, login, senha, lastPing, info, resources, lastCommand, commandTimestamp, commandResult, message)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      token,
      tipo,
      branch,
      login,
      senha,
      lastPing,
      info ? JSON.stringify(info) : null, // Verifique se é JSON antes de salvar
      resources ? JSON.stringify(resources) : null, // Verifique se é JSON antes de salvar
      lastCommand,
      commandTimestamp,
      commandResult,
      message
    ],
    (err) => {
      if (err) console.error('Erro ao salvar máquina:', err);
    }
  );
  
}



function loadMachines(callback) {
  db.all('SELECT * FROM machines', (err, rows) => {
    if (err) {
      console.error('Erro ao carregar máquinas:', err);
      callback({});
    } else {
      const machines = {};
      rows.forEach((row) => {
        machines[row.token] = {
          tipo: row.tipo,
          branch: row.branch,
          login: row.login,
          senha: row.senha,
          lastPing: row.lastPing,
          info: isJSON(row.info) ? JSON.parse(row.info) : null, // Verifica se é JSON antes de parsear
          resources: isJSON(row.resources) ? JSON.parse(row.resources) : null, // Verifica se é JSON antes de parsear
          lastCommand: row.lastCommand,
          commandTimestamp: row.commandTimestamp,
          commandResult: row.commandResult,
          message: row.message
        };
      });
      callback(machines);
    }
  });
}
function isJSON(str) {
  if (typeof str !== 'string') return false;
  try {
    JSON.parse(str);
    return true;
  } catch {
    return false;
  }
}


// Carrega máquinas do banco de dados na memória
let machines = {};
loadMachines((data) => {
  machines = data;
});

// Rotas
app.post('/register', (req, res) => {
  const { tipo, branch, login, senha } = req.body;
  const token = uuidv4.v4();

  const machine = {
    tipo,
    branch,
    login,
    senha,
    lastPing: new Date().toLocaleString('sv-SE', { timeZone: 'America/Sao_Paulo' }),
    info: null,
    resources: null,
    lastCommand: null,
    commandTimestamp: null,
    commandResult: null,
    message: null
  };
  machines[token] = machine;
  saveMachine(token, machine);

  res.send('Máquina registrada com sucesso.');
});

app.post('/login', (req, res) => {
  const { login, senha } = req.body;
  const token = Object.keys(machines).find(
    (key) => machines[key].login === login && machines[key].senha === senha
  );
  if (!token) return res.status(404).send('Login ou senha inválidos.');

  res.send(token);
});

app.post('/update', (req, res) => {
  const { token, info, resources } = req.body;
  if (!machines[token]) return res.status(404).send('Máquina não registrada.');

  machines[token] = {
    ...machines[token],
    lastPing: new Date().toLocaleString('sv-SE', { timeZone: 'America/Sao_Paulo' }),
    info: info || machines[token].info,
    resources: resources || machines[token].resources
  };
  saveMachine(token, machines[token]);
  res.send('Informações da máquina atualizadas.');
});

app.post('/command', (req, res) => {
  const { token, command } = req.body;
  if (!machines[token]) return res.status(404).send('Máquina não registrada.');
  if (!command) return res.status(400).send('Comando não fornecido.');

  machines[token].lastCommand = command;
  machines[token].commandTimestamp = new Date().toLocaleString('sv-SE', { timeZone: 'America/Sao_Paulo' });
  machines[token].commandResult = null;
  saveMachine(token, machines[token]);
  res.send('Comando enviado para a máquina.');
});

app.get('/get-command/:token', (req, res) => {
  const token = req.params.token;
  if (!machines[token]) return res.status(404).send('Máquina não encontrada.');

  const commandTimestamp = machines[token].commandTimestamp;
  const command = machines[token].lastCommand;

  if (command && commandTimestamp) {
    const elapsedTime = (new Date() - new Date(commandTimestamp)) / 1000;
    if (elapsedTime > 6) {
      machines[token].lastCommand = null;
      machines[token].commandTimestamp = null;
      saveMachine(token, machines[token]);
      return res.send('');
    }
  }

  machines[token].lastCommand = null;
  machines[token].commandTimestamp = null;
  saveMachine(token, machines[token]);
  res.send(command || '');
});

app.post('/command-result', (req, res) => {
  const { token, result } = req.body;
  if (!machines[token]) return res.status(404).send('Máquina não registrada.');

  machines[token].commandResult = result;
  saveMachine(token, machines[token]);
  res.send('Resultado do comando recebido.');
});

app.get('/command-result/:token', (req, res) => {
  const token = req.params.token;
  if (!machines[token]) return res.status(404).send('Máquina não encontrada.');

  res.send(machines[token].commandResult || 'Nenhum resultado disponível.');
});

// Função para enviar a mensagem
app.post('/send-message', (req, res) => {
  const { token, message } = req.body;
  if (!machines[token]) return res.status(404).send('Máquina não encontrada.');
  if (!message) return res.status(400).send('Mensagem não fornecida.');

  machines[token].message = message;
  machines[token].messageTimestamp = new Date().toLocaleString('sv-SE', { timeZone: 'America/Sao_Paulo' }); // Armazenando a hora em que a mensagem foi enviada
  saveMachine(token, machines[token]);
  res.send('Mensagem enviada para a máquina.');
});

// Função para pegar a mensagem
app.get('/get-message/:token', (req, res) => {
  const token = req.params.token;
  if (!machines[token]) return res.status(404).send('Máquina não encontrada.');

  const machine = machines[token];
  const messageTimestamp = machine.messageTimestamp;

  if (messageTimestamp) {
    const elapsedTime = (new Date() - new Date(messageTimestamp)) / 1000; // Tempo decorrido em segundos

    if (elapsedTime > 6) {
      // Se passou mais de 6 segundos, reseta a mensagem
      machines[token].message = null;
      machines[token].messageTimestamp = null;
      saveMachine(token, machines[token]);
      return res.send('');
    }
  }

  const message = machine.message;
  machines[token].message = null; 
  machines[token].messageTimestamp = null; // Reseta o timestamp da mensagem
  saveMachine(token, machines[token]);

  res.send(message || ''); 
});


app.get('/machine/:token', (req, res) => {
  const token = req.params.token;
  if (!machines[token]) return res.status(404).send('Máquina não encontrada.');

  const machine = machines[token];
  const isOnline = new Date() - new Date(machine.lastPing) < 15000;

  res.json({
    token,
    isOnline,
    info: machine.info,
    resources: machine.resources,
    lastPing: machine.lastPing
  });
});

app.get('/machines', (req, res) => {
  const allMachines = Object.entries(machines).map(([token, data]) => ({
    token,
    isOnline: new Date() - new Date(data.lastPing) < 15000,
    branch:data.branch,
    tipo: data.tipo,
    info: data.info,
    resources: data.resources,
    lastPing: data.lastPing
  }));

  res.json(allMachines);
});
app.post('/report-usage', (req, res) => {
  const { token, programUsage } = req.body;
  // console.log(req.body)

  if (!machines[token]) return res.status(404).send('Máquina não encontrada.');
  if (!programUsage) return res.status(400).send('Dados de uso do programa não fornecidos.');

  // Formatar a data como "YYYY-MM-DD"
  const today = new Date().toLocaleString('sv-SE', { timeZone: 'America/Sao_Paulo' }).split(' ')[0];  // Exemplo: "2024-11-30"

 
  for (const [programName, usage] of Object.entries(programUsage)) {
    const { windowTitle, usageTime } = usage;

 
    db.get(
      `SELECT * FROM program_usage WHERE token = ? AND program_name = ? AND window_title = ? AND timestamp = ?`,
      [token, programName, windowTitle, today],
      (err, row) => {
        if (err) {
          console.error('Erro ao verificar dados de uso do programa:', err);
          return res.status(500).send('Erro ao verificar dados de uso.');
        }

        if (row) {
          // Se já existe, atualize o tempo de uso
          const newUsageTime = row.usage_time + usageTime;
          db.run(
            `UPDATE program_usage SET usage_time = ? WHERE token = ? AND program_name = ? AND window_title = ? AND timestamp = ?`,
            [newUsageTime, token, programName, windowTitle, today],
            (err) => {
              if (err) {
                console.error('Erro ao atualizar dados de uso do programa:', err);
                return res.status(500).send('Erro ao atualizar dados de uso.');
              }
            }
          );
        } else {
          // Caso contrário, insira um novo registro
          db.run(
            `INSERT INTO program_usage (token, program_name, window_title, usage_time, timestamp)
             VALUES (?, ?, ?, ?, ?)`,
            [token, programName, windowTitle, usageTime, today],
            (err) => {
              if (err) {
                console.error('Erro ao salvar dados de uso do programa:', err);
                return res.status(500).send('Erro ao salvar dados de uso.');
              }
            }
          );
        }
      }
    );
  }

  res.send('Dados de uso do programa enviados com sucesso.');
});

app.get('/get-usage', (req, res) => {
  const { token, date } = req.query;  
 

  if (!token) {
    return res.status(400).send('Token não fornecido.');
  }

  
  const today = date || new Date().toLocaleString('sv-SE', { timeZone: 'America/Sao_Paulo' }).split(' ')[0];  // Exemplo: "2024-11-30"

  
  db.all(
    `SELECT * FROM program_usage WHERE token = ? AND timestamp = ? ORDER BY program_name, window_title`,
    [token, today],
    (err, rows) => {
      if (err) {
        console.error('Erro ao recuperar dados de uso:', err);
        return res.status(500).send('Erro ao recuperar dados de uso.');
      }

      if (rows.length === 0) {
        return res.status(404).send('Nenhum dado de uso encontrado para o token e data fornecidos.');
      }

      
      const groupedData = rows.reduce((acc, row) => {
        const programKey = row.program_name;
        if (!acc[programKey]) {
          acc[programKey] = {
            programName: programKey,
            usageTime: 0,
            windows: []
          };
        }
        acc[programKey].usageTime += row.usage_time;
        acc[programKey].windows.push({
          windowTitle: row.window_title,
          usageTime: row.usage_time
        });
        return acc;
      }, {});

      
      res.json(Object.values(groupedData));
    }
  );
});



const port = 3000;
app.listen(port, () => {
  console.log(`Servidor rodando em http://localhost:${port}`);
});
