import { AnalysisParams, AnalysisResult } from '../types';

declare global {
  interface Window {
    loadPyodide: any;
    pyodide: any;
  }
}

let pyodideInstance: any = null;

export const initPyodide = async () => {
  if (pyodideInstance) return pyodideInstance;

  try {
    const pyodide = await window.loadPyodide();
    await pyodide.loadPackage("numpy");
    
    // Fetch the Python logic from the separate file
    const response = await fetch('main.py');
    if (!response.ok) {
        throw new Error(`Failed to load python script: ${response.statusText}`);
    }
    const pythonCode = await response.text();
    
    await pyodide.runPythonAsync(pythonCode);
    
    pyodideInstance = pyodide;
    return pyodide;
  } catch (error) {
    console.error("Error loading Pyodide:", error);
    throw error;
  }
};

export const runAnalysis = async (params: AnalysisParams): Promise<AnalysisResult> => {
  if (!pyodideInstance) await initPyodide();
  
  const paramsJson = JSON.stringify(params);
  const code = `analyze_scenarios('${paramsJson}')`;
  
  try {
    const resultJson = await pyodideInstance.runPythonAsync(code);
    return JSON.parse(resultJson);
  } catch (e) {
    console.error("Python Calculation Error", e);
    throw e;
  }
};
