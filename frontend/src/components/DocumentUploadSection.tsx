import React, { useRef } from "react";
import { Upload, File } from "lucide-react";

interface DocumentUploadSectionProps {
  onUpload: (files: FileList) => void;
  isLoading: boolean;
}

const DocumentUploadSection: React.FC<DocumentUploadSectionProps> = ({
  onUpload,
  isLoading,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = React.useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUpload(e.dataTransfer.files);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      onUpload(e.target.files);
      e.target.value = "";
    }
  };

  return (
    <div
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
        dragActive ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white"
      }`}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleChange}
        accept=".pdf,.docx,.txt,.html,.htm"
        style={{ display: "none" }}
      />

      <div className="flex justify-center mb-4">
        <Upload size={48} className="text-blue-600" />
      </div>

      <h2 className="text-xl font-semibold text-gray-900 mb-2">
        Upload Documents
      </h2>
      <p className="text-gray-600 mb-4">
        Drag and drop files or click to browse
      </p>
      <p className="text-sm text-gray-500 mb-4">
        Supported formats: PDF, DOCX, TXT, HTML
      </p>

      <button
        onClick={() => fileInputRef.current?.click()}
        disabled={isLoading}
        className="inline-block bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
      >
        {isLoading ? "Uploading..." : "Browse Files"}
      </button>
    </div>
  );
};

export default DocumentUploadSection;
