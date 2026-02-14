import React, { useEffect, useState } from "react";
import { BarChart3, TrendingUp } from "lucide-react";
import toast from "react-hot-toast";
import { evaluationAPI, taskAPI } from "../services/api";

interface EvaluationReportProps {
  projectId: string;
}

const EvaluationReport: React.FC<EvaluationReportProps> = ({ projectId }) => {
  const [report, setReport] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    loadReport();
  }, [projectId]);

  const loadReport = async () => {
    setIsLoading(true);
    try {
      const data = await evaluationAPI.getReport(projectId);
      setReport(data);
    } catch (error) {
      toast.error("Failed to load evaluation report");
    } finally {
      setIsLoading(false);
    }
  };

  const runEvaluation = async () => {
    setRunning(true);
    try {
      const resp = await evaluationAPI.evaluateProject(projectId, { items: [] });
      const taskId = resp.task_id;
      toast.success("Evaluation started");
      // Poll task until completion
      let attempts = 0;
      const maxAttempts = 20;
      const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
      while (attempts < maxAttempts) {
        const status = await taskAPI.getStatus(taskId);
        if (status.status === "COMPLETED") {
          toast.success("Evaluation completed");
          await loadReport();
          break;
        }
        if (status.status === "FAILED") {
          toast.error("Evaluation failed");
          break;
        }
        attempts += 1;
        await delay(1000);
      }
    } catch (error) {
      toast.error("Failed to start evaluation");
    } finally {
      setRunning(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading evaluation report...</div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="bg-white rounded-lg shadow-md p-8 text-center">
        <p className="text-gray-600">No evaluation data available yet</p>
      </div>
    );
  }

  const { metrics, field_results, summary } = report;

  return (
    <div className="space-y-6">
      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Total Fields</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {metrics.total_fields}
              </p>
            </div>
            <BarChart3 size={32} className="text-blue-600" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">
                Matched Fields
              </p>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {metrics.matched_fields}
              </p>
            </div>
            <TrendingUp size={32} className="text-green-600" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Accuracy</p>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {(metrics.field_accuracy * 100).toFixed(1)}%
              </p>
            </div>
            <div className="w-12 h-12 rounded-full bg-yellow-100 flex items-center justify-center">
              <span className="font-semibold text-yellow-600">▼</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">
                Avg Confidence
              </p>
              <p className="text-3xl font-bold text-gray-900 mt-2">
                {(metrics.average_confidence * 100).toFixed(1)}%
              </p>
            </div>
            <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
              <span className="font-semibold text-purple-600">◆</span>
            </div>
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Summary</h2>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-blue-900">{summary}</p>
        </div>
      </div>

      {/* Field-Level Results */}
      {field_results && field_results.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Field-Level Performance
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-100">
                  <th className="px-4 py-2 text-left font-semibold text-gray-900">
                    Field Name
                  </th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-900">
                    Total
                  </th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-900">
                    Matched
                  </th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-900">
                    Accuracy
                  </th>
                </tr>
              </thead>
              <tbody>
                {field_results.map((result: any, idx: number) => (
                  <tr
                    key={idx}
                    className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}
                  >
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {result.field_name}
                    </td>
                    <td className="px-4 py-3 text-gray-600">{result.total}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {result.matched}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              result.accuracy > 0.8
                                ? "bg-green-500"
                                : result.accuracy > 0.6
                                  ? "bg-yellow-500"
                                  : "bg-red-500"
                            }`}
                            style={{ width: `${result.accuracy * 100}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium text-gray-900">
                          {(result.accuracy * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={runEvaluation}
          disabled={running}
          className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 disabled:bg-gray-400"
        >
          {running ? "Running Evaluation..." : "Run Evaluation"}
        </button>
        <button
          onClick={loadReport}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
        >
          Refresh Report
        </button>
      </div>
    </div>
  );
};

export default EvaluationReport;
