import React, { useState } from "react";
import { Download, AlertCircle, FileSpreadsheet } from "lucide-react";
import toast from "react-hot-toast";
import { comparisonAPI } from "../services/api";

interface ComparisonTableViewProps {
  data: any;
  projectId: string;
}

const ComparisonTableView: React.FC<ComparisonTableViewProps> = ({
  data,
  projectId,
}) => {
  const [exporting, setExporting] = useState(false);

  const handleExportCSV = async () => {
    setExporting(true);
    try {
      const csvContent = await comparisonAPI.exportCSV(projectId);
      const blob = new Blob([csvContent.content], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = csvContent.filename;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success("Table exported to CSV");
    } catch (error) {
      toast.error("Failed to export CSV");
    } finally {
      setExporting(false);
    }
  };

  const handleExportExcel = async () => {
    setExporting(true);
    try {
      const excelData = await comparisonAPI.exportExcel(projectId);
      // Decode base64 to binary
      const binaryString = atob(excelData.content_base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      const blob = new Blob([bytes], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = excelData.filename;
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success("Table exported to Excel");
    } catch (error) {
      toast.error("Failed to export Excel");
    } finally {
      setExporting(false);
    }
  };

  if (!data || !data.rows || data.rows.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-8 text-center">
        <AlertCircle size={48} className="mx-auto text-gray-400 mb-4" />
        <p className="text-gray-600">
          No extracted fields yet. Upload documents and run extraction.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">
          Comparison Table
        </h2>
        <div className="flex gap-2">
          <button
            onClick={handleExportCSV}
            disabled={exporting}
            className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:bg-gray-400 text-sm"
          >
            <Download size={18} />
            {exporting ? "Exporting..." : "Export CSV"}
          </button>
          <button
            onClick={handleExportExcel}
            disabled={exporting}
            className="flex items-center gap-2 bg-blue-700 text-white px-4 py-2 rounded-lg hover:bg-blue-800 disabled:bg-gray-400 text-sm"
          >
            <FileSpreadsheet size={18} />
            {exporting ? "Exporting..." : "Export Excel"}
          </button>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-gray-100">
              <th className="border border-gray-300 px-4 py-2 text-left font-semibold text-gray-900">
                Field Name
              </th>
              <th className="border border-gray-300 px-4 py-2 text-left font-semibold text-gray-900">
                Type
              </th>
              {data.documents.map((doc: any) => (
                <th
                  key={doc.id}
                  className="border border-gray-300 px-4 py-2 text-left font-semibold text-gray-900 max-w-xs"
                >
                  <div className="truncate">{doc.filename}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row: any, idx: number) => (
              <tr
                key={idx}
                className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}
              >
                <td className="border border-gray-300 px-4 py-3 font-medium text-gray-900">
                  {row.field_name}
                </td>
                <td className="border border-gray-300 px-4 py-3 text-sm text-gray-600">
                  {row.field_type}
                </td>
                {data.documents.map((doc: any) => {
                  const result = row.document_results[doc.id] || {};
                  const confidence = result.confidence_score || 0;
                  const value = result.extracted_value || "N/A";
                  const citations = Array.isArray(result.citations)
                    ? result.citations
                    : [];

                  return (
                    <td
                      key={`${idx}-${doc.id}`}
                      className="border border-gray-300 px-4 py-3"
                    >
                      <div className="text-sm text-gray-900">{value}</div>
                      {citations.length > 0 && (
                        <details className="mt-2 group">
                          <summary className="cursor-pointer text-xs text-blue-700 hover:text-blue-800">
                            View citations ({citations.length})
                          </summary>
                          <div className="mt-2 border rounded bg-gray-50 p-2">
                            <ul className="space-y-2">
                              {citations.slice(0, 3).map((c: any, i: number) => (
                                <li key={i} className="text-xs text-gray-800">
                                  <div className="font-medium">
                                    {c.section_title
                                      ? c.section_title
                                      : "Citation"}
                                    {typeof c.page_number === "number" && (
                                      <span className="ml-1 text-gray-600">
                                        • p.{c.page_number}
                                      </span>
                                    )}
                                    {typeof c.relevance_score === "number" && (
                                      <span className="ml-1 text-gray-600">
                                        • score {c.relevance_score.toFixed(2)}
                                      </span>
                                    )}
                                  </div>
                                  <div className="text-gray-700">
                                    {c.citation_text}
                                  </div>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </details>
                      )}
                      {confidence > 0 && (
                        <div className="mt-1">
                          <div className="w-full bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                confidence > 0.8
                                  ? "bg-green-500"
                                  : confidence > 0.6
                                    ? "bg-yellow-500"
                                    : "bg-red-500"
                              }`}
                              style={{ width: `${confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-gray-600">
                            {(confidence * 100).toFixed(0)}% confidence
                          </span>
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-4 text-sm text-gray-600">
        <p>
          Total fields: <strong>{data.row_count}</strong> | Documents:{" "}
          <strong>{data.document_count}</strong>
        </p>
      </div>
    </div>
  );
};

export default ComparisonTableView;
