import express from 'express';
import fs from 'fs';
import path from 'path';
import { Network } from './network';
import { Node, Edge } from './types';
import { AIService } from './aiService';

const app = express();
app.use(express.json());

const dataPath = path.join(__dirname, '..', '..', 'data', 'network_dummy.json');
const rawData = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
const dummyNodes: Node[] = rawData.nodes;
const dummyEdges: Edge[] = rawData.edges;

const network = new Network(dummyNodes, dummyEdges);

app.get('/network', (req, res) => {
  res.json({ nodes: network.getNodes(), edges: dummyEdges });
});

app.post('/simulate-failure', (req, res) => {
  const { failed_ids } = req.body;
  const result = network.simulateFailure(failed_ids);
  res.json(result);
});

app.post('/simulate-cascade', (req, res) => {
  const { failed_ids } = req.body;
  const result = network.simulateCascade(failed_ids);
  res.json(result);
});

app.get('/criticality', (req, res) => {
  res.json(network.getCriticality());
});

app.post('/explain', async (req, res) => {
  const simulation = req.body;
  const result = await AIService.explainFailure(simulation);
  res.json(result);
});

app.post('/explain-cascade', async (req, res) => {
  const cascade = req.body;
  const result = await AIService.explainCascade(cascade);
  res.json(result);
});

app.post('/nl-query', async (req, res) => {
  const { query } = req.body;
  const failedIds = await AIService.mapQueryToNodes(query, network.getNodes());
  res.json({ failed_ids: failedIds });
});

app.post('/generate-report', async (req, res) => {
  const simulationData = req.body;
  const report = await AIService.generateResilienceReport(simulationData);
  res.json(report);
});

const PORT = 3000;
app.listen(PORT, () => {
  console.log(`Backend running at http://localhost:${PORT}`);
});
