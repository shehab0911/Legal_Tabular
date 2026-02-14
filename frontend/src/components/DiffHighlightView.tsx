import React, { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle, GitCompare, ChevronDown, ChevronRight } from "lucide-react";
import toast from "react-hot-toast";
import { diffAPI } from "../services/api";

interface DiffHighlightViewProps {
  projectId: string;
}

interface DiffField {
  field_name: string;
  is_unanimous: boolean;
  majority_value: string;
  majority_count: number;
  total_documents: number;
  unique_values: number;
  value_groups: Record<string, string[]>;
  outliers: Array<{
    document: string;
    value: string;
    document_id: string;
    confidence: number;
  }>;
  document_values: Record<string, { value: string; confidence: number; document_id: string }>;
  similarity_pairs: Array<{ doc_a: string; doc_b: string; similarity: number }>;
}

interface DiffData {
  project_id: string;
  field_diffs: DiffField[];
  summary: {
    total_fields: number;
    fields_with_differences: number;
    unanimity_rate: number;
  };
}

const DiffHighlightView: React.FC<DiffHighlightViewProps> = ({ projectId }) => {
  const [diffData, setDiffData] = useState<DiffData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set());
  const [filterMode, setFilterMode] = useState<"all" | "differences" | "unanimous">("all");

  useEffect(() => {
    loadDiff();
  }, [projectId]);

  const loadDiff = async () => {
    setIsLoading(true);
    try {
      const data = await diffAPI.getDiff(projectId);
      setDiffData(data);
      // Auto-expand fields with differences
      const diffs = new Set<string>();
      (data.field_diffs || []).forEach((f: DiffField) => {
        if (!f.is_unanimous) diffs.add(f.field_name);
      });
      setExpandedFields(diffs);
    } catch (error) {
      toast.error("Failed to load diff data");
    } finally {
      setIsLoading(false);
    }
  };

  const toggleField = (fieldName: string) => {
    setExpandedFields((prev) => {
      const next = new Set(prev);
      if (next.has(fieldName)) next.delete(fieldName);
      else next.add(fieldName);
      return next;
    });
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Computing cross-document differences...</div>
      </div>
    );
  }

  if (!diffData || !diffData.field_diffs || diffData.field_diffs.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-8 text-center">
        <GitCompare size={48} className="mx-auto text-gray-400 mb-4" />
        <p className="text-gray-600">
          No extraction data available. Upload documents and run extraction first.
        </p>
      </div>
    );
  }

  const filteredFields = diffData.field_diffs.filter((f) => {
    if (filterMode === "differences") return !f.is_unanimous;
    if (filterMode === "unanimous") return f.is_unanimous;
    return true;
  });

  const { summary } = diffData;

  return (
    <div className="space-y-6">
      {/* Summary Banner */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-semibold text-gray-900">Diff Highlighting</h2>
          <button
            onClick={loadDiff}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm"
          >
            Refresh
          </button>
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-blue-50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-blue-700">{summary.total_fields}</p>
            <p className="text-sm text-blue-600">Total Fields</p>
          </div>
          <div className="bg-red-50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-red-700">{summary.fields_with_differences}</p>
            <p className="text-sm text-red-600">Fields with Differences</p>
          </div>
          <div className="bg-green-50 rounded-lg p-4 text-center">
            <p className="text-2xl font-bold text-green-700">
              {(summary.unanimity_rate * 100).toFixed(0)}%
            </p>
            <p className="text-sm text-green-600">Unanimity Rate</p>
          </div>
        </div>
      </div>

      {/* Filter Buttons */}
      <div className="flex gap-2">
        {(["all", "differences", "unanimous"] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => setFilterMode(mode)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filterMode === mode
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-50"
            }`}
          >
            {mode === "all"
              ? `All (${diffData.field_diffs.length})`
              : mode === "differences"
                ? `Differences (${summary.fields_with_differences})`
                : `Unanimous (${summary.total_fields - summary.fields_with_differences})`}
          </button>
        ))}
      </div>

      {/* Field Diffs */}
      <div className="space-y-3">
        {filteredFields.map((field) => {
          const isExpanded = expandedFields.has(field.field_name);
          return (
            <div
              key={field.field_name}
              className={`bg-white rounded-lg shadow-md overflow-hidden border-l-4 ${
                field.is_unanimous ? "border-green-500" : "border-red-500"
              }`}
            >
              {/* Field Header */}
              <button
                onClick={() => toggleField(field.field_name)}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {isExpanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
                  {field.is_unanimous ? (
                    <CheckCircle size={20} className="text-green-500" />
                  ) : (
                    <AlertTriangle size={20} className="text-red-500" />
                  )}
                  <span className="font-semibold text-gray-900">{field.field_name}</span>
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-600">
                  <span>{field.unique_values} unique value{field.unique_values > 1 ? "s" : ""}</span>
                  <span>{field.total_documents} doc{field.total_documents > 1 ? "s" : ""}</span>
                  {!field.is_unanimous && (
                    <span className="bg-red-100 text-red-800 px-2 py-0.5 rounded-full text-xs font-medium">
                      {field.outliers.length} outlier{field.outliers.length > 1 ? "s" : ""}
                    </span>
                  )}
                </div>
              </button>

              {/* Expanded Details */}
              {isExpanded && (
                <div className="px-4 pb-4 border-t border-gray-100">
                  {/* Majority Value */}
                  <div className="mt-3 mb-4">
                    <p className="text-xs font-medium text-gray-500 uppercase mb-1">Majority Value</p>
                    <div className="bg-green-50 border border-green-200 rounded p-3">
                      <p className="text-sm text-green-900">{field.majority_value}</p>
                      <p className="text-xs text-green-600 mt-1">
                        Agreed by {field.majority_count} of {field.total_documents} documents
                      </p>
                    </div>
                  </div>

                  {/* Per-Document Values */}
                  <div className="mb-4">
                    <p className="text-xs font-medium text-gray-500 uppercase mb-2">Document Values</p>
                    <div className="space-y-2">
                      {Object.entries(field.document_values).map(([docName, info]) => {
                        const isOutlier = field.outliers.some((o) => o.document === docName);
                        return (
                          <div
                            key={docName}
                            className={`flex items-center justify-between p-2 rounded text-sm ${
                              isOutlier
                                ? "bg-red-50 border border-red-200"
                                : "bg-gray-50 border border-gray-200"
                            }`}
                          >
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-gray-900 truncate">{docName}</p>
                              <p className={`text-sm ${isOutlier ? "text-red-700 font-medium" : "text-gray-600"}`}>
                                {info.value}
                              </p>
                            </div>
                            <div className="flex items-center gap-2 ml-4 flex-shrink-0">
                              <span className="text-xs text-gray-500">
                                {(info.confidence * 100).toFixed(0)}%
                              </span>
                              {isOutlier && (
                                <span className="bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded-full">
                                  OUTLIER
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Similarity Pairs */}
                  {field.similarity_pairs.length > 0 && (
                    <div>
                      <p className="text-xs font-medium text-gray-500 uppercase mb-2">Pairwise Similarity</p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {field.similarity_pairs.map((pair, idx) => (
                          <div
                            key={idx}
                            className="flex items-center justify-between bg-gray-50 rounded p-2 text-xs"
                          >
                            <span className="text-gray-700 truncate flex-1">
                              {pair.doc_a} vs {pair.doc_b}
                            </span>
                            <span
                              className={`ml-2 font-semibold ${
                                pair.similarity > 0.8
                                  ? "text-green-600"
                                  : pair.similarity > 0.5
                                    ? "text-yellow-600"
                                    : "text-red-600"
                              }`}
                            >
                              {(pair.similarity * 100).toFixed(0)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {filteredFields.length === 0 && (
        <div className="bg-white rounded-lg shadow-md p-8 text-center">
          <p className="text-gray-600">No fields match the current filter.</p>
        </div>
      )}
    </div>
  );
};

export default DiffHighlightView;
