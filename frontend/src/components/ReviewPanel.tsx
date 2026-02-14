import React, { useEffect, useState } from "react";
import { Check, X, Edit } from "lucide-react";
import toast from "react-hot-toast";
import { reviewAPI } from "../services/api";

interface ReviewPanelProps {
  projectId: string;
}

const ReviewPanel: React.FC<ReviewPanelProps> = ({ projectId }) => {
  const [reviews, setReviews] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [reviewerName, setReviewerName] = useState("reviewer");

  useEffect(() => {
    loadReviews();
  }, [projectId]);

  const loadReviews = async () => {
    setIsLoading(true);
    try {
      const data = await reviewAPI.getPendingReviews(projectId);
      setReviews(data.reviews || []);
    } catch (error) {
      toast.error("Failed to load reviews");
    } finally {
      setIsLoading(false);
    }
  };

  const handleReview = async (
    extractionId: string,
    status: string,
    manualValue?: string,
  ) => {
    try {
      await reviewAPI.reviewExtraction(
        extractionId,
        status,
        manualValue,
        editNotes,
        reviewerName,
      );
      toast.success(`Review updated: ${status}`);
      setEditingId(null);
      await loadReviews();
    } catch (error) {
      toast.error("Failed to update review");
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading reviews...</div>
      </div>
    );
  }

  if (reviews.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-8 text-center">
        <p className="text-gray-600">No pending reviews</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-2xl font-semibold text-gray-900 mb-6">
        Review Extractions
      </h2>
      <div className="space-y-4">
        {reviews.map((review) => (
          <div
            key={review.id}
            className="border border-gray-200 rounded-lg p-4"
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-semibold text-gray-900">
                  {review.field_name
                    ? review.field_name
                        .replace(/_/g, " ")
                        .replace(/\b\w/g, (c: string) => c.toUpperCase())
                    : "Unknown Field"}
                </h3>
                <p className="text-sm text-gray-600">
                  Status: <span className="font-medium">{review.status}</span> • Confidence: {(review.confidence_score * 100).toFixed(0)}%
                </p>
              </div>
              <div className="flex gap-2">
                {editingId === review.id ? (
                  <>
                    <button
                      onClick={() =>
                        handleReview(
                          review.extraction_id,
                          "CONFIRMED",
                          editValue,
                        )
                      }
                      className="flex items-center gap-1 bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 text-sm"
                    >
                      <Check size={16} />
                      Confirm
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="flex items-center gap-1 bg-gray-400 text-white px-3 py-1 rounded hover:bg-gray-500 text-sm"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() =>
                        handleReview(review.extraction_id, "CONFIRMED")
                      }
                      className="flex items-center gap-1 bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 text-sm"
                    >
                      <Check size={16} />
                      Approve
                    </button>
                    <button
                      onClick={() =>
                        handleReview(review.extraction_id, "REJECTED")
                      }
                      className="flex items-center gap-1 bg-red-600 text-white px-3 py-1 rounded hover:bg-red-700 text-sm"
                    >
                      <X size={16} />
                      Reject
                    </button>
                    <button
                      onClick={() => {
                        setEditingId(review.id);
                        setEditValue(review.ai_value || "");
                        setEditNotes("");
                      }}
                      className="flex items-center gap-1 bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 text-sm"
                    >
                      <Edit size={16} />
                      Edit
                    </button>
                  </>
                )}
              </div>
            </div>

            {editingId === review.id ? (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Manual Value
                  </label>
                  <textarea
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    rows={3}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Notes
                  </label>
                  <textarea
                    value={editNotes}
                    onChange={(e) => setEditNotes(e.target.value)}
                    className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                    rows={2}
                    placeholder="Optional review notes..."
                  />
                </div>
              </div>
            ) : (
              <div className="bg-gray-50 p-3 rounded">
                <p className="text-sm text-gray-900">
                  <strong>AI Value:</strong> {review.ai_value || "N/A"}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default ReviewPanel;
