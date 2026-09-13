import Anthropic from '@anthropic-ai/sdk';
import { Node, SimulationResult, CascadeResult } from './types';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY || 'your-api-key-here',
});

export class AIService {
  public static async explainFailure(data: SimulationResult): Promise<{ narrative: string, recommendation: string }> {
    const prompt = `You are an infrastructure analyst. Generate an incident brief based on this simulation data:
${JSON.stringify(data, null, 2)}

Constraints:
- ONLY reference numbers present in the input JSON.
- NEVER estimate, round dramatically, or invent new statistics.
- Avoid commenting on the structural or engineering condition of any asset.
- Tone: Plain-English, professional, for a city planner.

Return ONLY a JSON object:
{
  "narrative": "3-5 sentence concrete incident brief using the input numbers.",
  "recommendation": "1-3 sentence actionable mitigation recommendation."
}`;

    try {
      const response = await anthropic.messages.create({
        model: 'claude-3-5-sonnet-20240620',
        max_tokens: 1000,
        messages: [{ role: 'user', content: prompt }],
      });

      const text = response.content[0].type === 'text' ? response.content[0].text : '';
      const match = text.match(/\{.*?\}/s);
      if (!match) throw new Error('Invalid AI response');
      return JSON.parse(match[0]);
    } catch (error) {
      console.error('AI explain error:', error);
      return { narrative: 'Error generating narrative.', recommendation: 'Manual review required.' };
    }
  }

  public static async explainCascade(data: CascadeResult): Promise<{ narrative: string, recommendation: string }> {
    const prompt = `You are an infrastructure analyst. Narrate this failure chain reaction:
${JSON.stringify(data, null, 2)}

Constraints:
- Narrate the chain reaction across rounds (e.g., "Round 1 closed X; Round 2, Y overloaded and failed, cutting off Z more people").
- ONLY reference numbers present in the input JSON.
- Escalate the tone appropriately as the cumulative_impact_score climbs, but avoid melodrama or inventing details.
- Avoid commenting on the structural or engineering condition of any asset.

Return ONLY a JSON object:
{
  "narrative": "Concrete narration of the cascade sequence.",
  "recommendation": "Strategic recommendation to stop such cascades."
}`;

    try {
      const response = await anthropic.messages.create({
        model: 'claude-3-5-sonnet-20240620',
        max_tokens: 1000,
        messages: [{ role: 'user', content: prompt }],
      });

      const text = response.content[0].type === 'text' ? response.content[0].text : '';
      const match = text.match(/\{.*?\}/s);
      if (!match) throw new Error('Invalid AI response');
      return JSON.parse(match[0]);
    } catch (error) {
      console.error('AI cascade explain error:', error);
      return { narrative: 'Error generating cascade narrative.', recommendation: 'Manual review required.' };
    }
  }

  public static async mapQueryToNodes(query: string, nodes: Node[]): Promise<string[]> {
    const nodeList = nodes.map(n => `${n.id} (${n.name}, ${n.type})`).join('\n');

    const prompt = `You are an infrastructure mapping assistant.
Given the following list of real network nodes:
${nodeList}

The user query is: "${query}".

Identify which node IDs from the list the user is referring to.
Return ONLY a JSON object: { "failed_ids": ["id1", "id2", ...] }.
If you cannot confidently match a node, return an empty list.
Do NOT invent IDs.`;

    try {
      const response = await anthropic.messages.create({
        model: 'claude-3-5-sonnet-20240620',
        max_tokens: 1000,
        messages: [{ role: 'user', content: prompt }],
      });

      const text = response.content[0].type === 'text' ? response.content[0].text : '';
      const match = text.match(/\{.*?\}/s);
      if (!match) return [];

      const parsed = JSON.parse(match[0]);
      return parsed.failed_ids || [];
    } catch (error) {
      console.error('AI mapping error:', error);
      return [];
    }
  }

  public static async generateResilienceReport(data: any): Promise<{ title: string, sections: { heading: string, body: string }[] }> {
    const prompt = `You are a professional city planner. Generate a resilience report based on the following simulation data:
${JSON.stringify(data, null, 2)}

Structure the response as a JSON object:
{
  "title": "...",
  "sections": [
    { "heading": "Executive Summary", "body": "..." },
    { "heading": "Human Impact", "body": "..." },
    { "heading": "Most Critical Assets", "body": "..." },
    { "heading": "Recommendation", "body": "..." }
  ]
}

Use a factual, plain-language tone. Use only the numbers provided in the data.
Do not hallucinate external facts or estimate impact.`;

    try {
      const response = await anthropic.messages.create({
        model: 'claude-3-5-sonnet-20240620',
        max_tokens: 2000,
        messages: [{ role: 'user', content: prompt }],
      });

      const text = response.content[0].type === 'text' ? response.content[0].text : '';
      const match = text.match(/\{.*?\}/s);
      if (!match) throw new Error('Could not parse JSON from AI response');

      return JSON.parse(match[0]);
    } catch (error) {
      console.error('AI report error:', error);
      return {
        title: 'Network Resilience Report',
        sections: [{ heading: 'Error', body: 'Could not generate report automatically.' }]
      };
    }
  }
}
