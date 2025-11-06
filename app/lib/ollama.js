// Ollama client for Next.js API routes
// This is a server-side utility for interacting with Ollama

import { getOllamaUrl } from './server-utils';

const OLLAMA_BASE_URL = getOllamaUrl();

/**
 * Chat with Ollama and get JSON response
 * @param {string} model - Model name (e.g., 'llama3.2')
 * @param {string} prompt - The prompt to send
 * @param {object} options - Additional options
 * @returns {Promise<object>} JSON response from Ollama
 */
export async function ollamaChatJSON(model, prompt, options = {}) {
  try {
    const url = `${OLLAMA_BASE_URL.replace(/\/$/, '')}/api/chat`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: model || 'llama3.2',
        messages: [
          {
            role: 'user',
            content: prompt
          }
        ],
        format: 'json',
        stream: false,
        ...options
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Ollama API error: ${response.status} ${errorText}`);
    }

    const data = await response.json();
    
    // Extract JSON from response
    if (data.message?.content) {
      try {
        return JSON.parse(data.message.content);
      } catch (parseError) {
        // If not valid JSON, return the content as-is
        return { content: data.message.content };
      }
    }
    
    return data;
  } catch (error) {
    console.error('[Ollama] Error:', error);
    throw error;
  }
}

/**
 * Generate text using Ollama
 * @param {string} model - Model name
 * @param {string} prompt - The prompt
 * @returns {Promise<string>} Generated text
 */
export async function ollamaGenerate(model, prompt) {
  try {
    const url = `${OLLAMA_BASE_URL.replace(/\/$/, '')}/api/generate`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: model || 'llama3.2',
        prompt,
        stream: false,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Ollama API error: ${response.status} ${errorText}`);
    }

    const data = await response.json();
    return data.response || '';
  } catch (error) {
    console.error('[Ollama] Error:', error);
    throw error;
  }
}

