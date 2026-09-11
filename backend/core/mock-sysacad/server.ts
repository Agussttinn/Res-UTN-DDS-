import express from 'express';
import { router } from './router';

const PORT = process.env.MOCK_SYSACAD_PORT ? Number(process.env.MOCK_SYSACAD_PORT) : 4000;

const app = express();
app.use(router);

app.listen(PORT, () => {
  console.log(`Mock SySACAD escuchando en http://localhost:${PORT}`);
});
