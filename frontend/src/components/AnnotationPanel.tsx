import React, { useEffect, useState } from "react";
import { MessageSquare, Plus, Edit, Trash2, Send, X } from "lucide-react";
import toast from "react-hot-toast";
import { annotationAPI, extractionListAPI } from "../services/api";

interface AnnotationPanelProps {
  projectId: string;
}

interface AnnotationData {
  id: string;
  extraction_id: string;
  comment_text: string;
  annotated_by: string;
  created_at: string;
  updated_at: string;
}

interface ExtractionItem {
  id: string;
  document_id: string;
  field_name: string;
  field_type: string;
  extracted_value?: string;
  normalized_value?: string;
  confidence_score: number;
  status: string;
}

const AnnotationPanel: React.FC<AnnotationPanelProps> = ({ projectId }) => {
  const [annotations, setAnnotations] = useState<AnnotationData[]>([]);
  const [extractions, setExtractions] = useState<ExtractionItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // New annotation form
  const [showForm, setShowForm] = useState(false);
  const [selectedExtractionId, setSelectedExtractionId] = useState<string>("");
  const [commentText, setCommentText] = useState("");
  const [annotatedBy, setAnnotatedBy] = useState("reviewer");

  // Edit state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  // Filter
  const [filterExtractionId, setFilterExtractionId] = useState<string>("");

  useEffect(() => {
    loadData();
  }, [projectId]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [annotData, extData] = await Promise.all([
        annotationAPI.listProjectAnnotations(projectId),
        extractionListAPI.listExtractions(projectId),
      ]);
      setAnnotations(annotData.annotations || []);
      setExtractions(extData.extractions || []);
    } catch (error) {
      toast.error("Failed to load annotations");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!selectedExtractionId || !commentText.trim()) {
      toast.error("Select a field and enter a comment");
      return;
    }
    try {
      await annotationAPI.createAnnotation(selectedExtractionId, commentText, annotatedBy);
      toast.success("Annotation created");
      setShowForm(false);
      setCommentText("");
      setSelectedExtractionId("");
      await loadData();
    } catch (error) {
      toast.error("Failed to create annotation");
    }
  };

  const handleUpdate = async (annotationId: string) => {
    if (!editText.trim()) return;
    try {
      await annotationAPI.updateAnnotation(annotationId, editText);
      toast.success("Annotation updated");
      setEditingId(null);
      setEditText("");
      await loadData();
    } catch (error) {
      toast.error("Failed to update annotation");
    }
  };

  const handleDelete = async (annotationId: string) => {
    if (!window.confirm("Delete this annotation?")) return;
    try {
      await annotationAPI.deleteAnnotation(annotationId);
      toast.success("Annotation deleted");
      await loadData();
    } catch (error) {
      toast.error("Failed to delete annotation");
    }
  };

  const getFieldLabel = (extractionId: string): string => {
    const ext = extractions.find((e) => e.id === extractionId);
    if (!ext) return extractionId.substring(0, 8) + "...";
    return ext.field_name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  };

  const filteredAnnotations = filterExtractionId
    ? annotations.filter((a) => a.extraction_id === filterExtractionId)
    : annotations;

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading annotations...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-semibold text-gray-900">Annotations</h2>
          <div className="flex gap-2">
            <button
              onClick={loadData}
              className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300 text-sm"
            >
              Refresh
            </button>
            <button
              onClick={() => setShowForm(!showForm)}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm"
            >
              <Plus size={16} />
              New Annotation
            </button>
          </div>
        </div>

        <p className="text-sm text-gray-600">
          {annotations.length} annotation{annotations.length !== 1 ? "s" : ""} across{" "}
          {new Set(annotations.map((a) => a.extraction_id)).size} fields
        </p>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-500">
          <h3 className="font-semibold text-gray-900 mb-4">New Annotation</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Field</label>
              <select
                value={selectedExtractionId}
                onChange={(e) => setSelectedExtractionId(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              >
                <option value="">Select a field...</option>
                {extractions.map((ext) => (
                  <option key={ext.id} value={ext.id}>
                    {ext.field_name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                    {" "}- {(ext.extracted_value || "N/A").substring(0, 60)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Author</label>
              <input
                type="text"
                value={annotatedBy}
                onChange={(e) => setAnnotatedBy(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                placeholder="Your name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Comment</label>
              <textarea
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                rows={3}
                placeholder="Add your review comment, risk flag, or observation..."
              />
            </div>

            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
              >
                <Send size={16} />
                Submit
              </button>
              <button
                onClick={() => {
                  setShowForm(false);
                  setCommentText("");
                  setSelectedExtractionId("");
                }}
                className="flex items-center gap-2 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300"
              >
                <X size={16} />
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Filter */}
      {extractions.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Filter by Field</label>
          <select
            value={filterExtractionId}
            onChange={(e) => setFilterExtractionId(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
          >
            <option value="">All fields</option>
            {extractions.map((ext) => (
              <option key={ext.id} value={ext.id}>
                {ext.field_name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Annotations List */}
      {filteredAnnotations.length === 0 ? (
        <div className="bg-white rounded-lg shadow-md p-8 text-center">
          <MessageSquare size={48} className="mx-auto text-gray-400 mb-4" />
          <p className="text-gray-600">No annotations yet. Create one to start collaborating.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredAnnotations.map((ann) => (
            <div key={ann.id} className="bg-white rounded-lg shadow-md p-4 border-l-4 border-yellow-400">
              <div className="flex justify-between items-start mb-2">
                <div>
                  <span className="inline-block bg-blue-100 text-blue-800 text-xs font-medium px-2 py-0.5 rounded mr-2">
                    {getFieldLabel(ann.extraction_id)}
                  </span>
                  <span className="text-xs text-gray-500">
                    by <strong>{ann.annotated_by}</strong> on{" "}
                    {new Date(ann.created_at).toLocaleString()}
                  </span>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => {
                      setEditingId(ann.id);
                      setEditText(ann.comment_text);
                    }}
                    className="text-gray-400 hover:text-blue-600 p-1"
                    title="Edit"
                  >
                    <Edit size={16} />
                  </button>
                  <button
                    onClick={() => handleDelete(ann.id)}
                    className="text-gray-400 hover:text-red-600 p-1"
                    title="Delete"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              {editingId === ann.id ? (
                <div className="space-y-2">
                  <textarea
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                    rows={3}
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleUpdate(ann.id)}
                      className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => {
                        setEditingId(null);
                        setEditText("");
                      }}
                      className="bg-gray-200 text-gray-800 px-3 py-1 rounded text-sm hover:bg-gray-300"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-gray-800 whitespace-pre-wrap">{ann.comment_text}</p>
              )}

              {ann.updated_at !== ann.created_at && (
                <p className="text-xs text-gray-400 mt-2">
                  Updated: {new Date(ann.updated_at).toLocaleString()}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default AnnotationPanel;
