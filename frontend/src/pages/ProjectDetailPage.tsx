import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Upload, Table, Eye, BarChart3, Settings, RefreshCw, Trash2,
  GitCompare, MessageSquare,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { projectAPI, documentAPI, extractionAPI, comparisonAPI, taskAPI } from '../services/api';
import { useStore } from '../store/appStore';
import DocumentUploadSection from '../components/DocumentUploadSection';
import ComparisonTableView from '../components/ComparisonTableView';
import ReviewPanel from '../components/ReviewPanel';
import EvaluationReport from '../components/EvaluationReport';
import DiffHighlightView from '../components/DiffHighlightView';
import AnnotationPanel from '../components/AnnotationPanel';
import FieldTemplateManager from '../components/FieldTemplateManager';

export const ProjectDetailPage: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { currentProject, setCurrentProject, activeTab, setActiveTab, isLoading, setIsLoading } = useStore();
  const [documents, setDocuments] = useState<any[]>([]);
  const [extracting, setExtracting] = useState(false);
  const [tableData, setTableData] = useState<any>(null);
  const [extractionTaskId, setExtractionTaskId] = useState<string | null>(null);

  useEffect(() => {
    if (projectId) {
      loadProject();
    }
  }, [projectId]);

  // Poll extraction task status
  useEffect(() => {
    if (!extractionTaskId) return;
    let cancelled = false;
    const poll = async () => {
      let attempts = 0;
      while (!cancelled && attempts < 120) {
        try {
          const status = await taskAPI.getStatus(extractionTaskId);
          if (status.status === 'COMPLETED') {
            toast.success('Extraction completed successfully');
            setExtracting(false);
            setExtractionTaskId(null);
            await loadProject();
            return;
          }
          if (status.status === 'FAILED') {
            toast.error('Extraction failed: ' + (status.error_message || 'Unknown error'));
            setExtracting(false);
            setExtractionTaskId(null);
            return;
          }
        } catch (e) {
          // ignore poll errors
        }
        attempts++;
        await new Promise((r) => setTimeout(r, 2000));
      }
    };
    poll();
    return () => { cancelled = true; };
  }, [extractionTaskId]);

  const loadProject = async () => {
    setIsLoading(true);
    try {
      const project = await projectAPI.getProject(projectId!);
      setCurrentProject(project);
      await loadDocuments();
    } catch (error) {
      toast.error('Failed to load project');
      navigate('/projects');
    } finally {
      setIsLoading(false);
    }
  };

  const loadDocuments = async () => {
    try {
      const data = await documentAPI.listDocuments(projectId!);
      setDocuments(data.documents || []);
    } catch (error) {
      toast.error('Failed to load documents');
    }
  };

  const handleDocumentUpload = async (files: FileList) => {
    if (!files || files.length === 0) return;

    setIsLoading(true);
    try {
      const failedUploads: { name: string; reason: string }[] = [];
      const fileArray = Array.from(files);
      
      for (let i = 0; i < fileArray.length; i++) {
        const file = fileArray[i];
        try {
          await documentAPI.uploadDocument(projectId!, file);
          toast.success(`Uploaded ${file.name}`);
        } catch (error: any) {
          const reason =
            error?.response?.data?.detail ||
            error?.message ||
            'Upload failed';
          failedUploads.push({ name: file.name, reason });
        }
      }

      await loadDocuments();
      await loadProject();
      if (failedUploads.length > 0) {
        const names = failedUploads.map((item) => item.name).join(', ');
        toast.error(`Failed: ${names}`);
      }
    } catch (error) {
      toast.error('Failed to upload documents');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExtractFields = async () => {
    setExtracting(true);
    try {
      const result = await extractionAPI.extractFields(projectId!);
      toast.success('Extraction started - tracking progress...');
      setExtractionTaskId(result.task_id);
    } catch (error) {
      toast.error('Failed to start extraction');
      setExtracting(false);
    }
  };

  const loadComparisonTable = async () => {
    setIsLoading(true);
    try {
      const data = await comparisonAPI.getTable(projectId!);
      setTableData(data);
      setActiveTab('table');
    } catch (error) {
      toast.error('Failed to load comparison table');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteProject = async () => {
    if (!projectId) return;
    const confirmed = window.confirm('Are you sure you want to delete this project? This action cannot be undone.');
    if (!confirmed) return;
    setIsLoading(true);
    try {
      await projectAPI.deleteProject(projectId);
      toast.success('Project deleted');
      navigate('/projects');
    } catch (error) {
      toast.error('Failed to delete project');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading && !currentProject) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="text-gray-500">Loading project...</div>
      </div>
    );
  }

  if (!currentProject) return null;

  const tabs = [
    { id: 'documents', label: 'Documents', icon: Upload },
    { id: 'table', label: 'Comparison Table', icon: Table },
    { id: 'diff', label: 'Diff Highlighting', icon: GitCompare },
    { id: 'review', label: 'Review', icon: Eye },
    { id: 'annotations', label: 'Annotations', icon: MessageSquare },
    { id: 'evaluation', label: 'Evaluation', icon: BarChart3 },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{currentProject.name}</h1>
              <p className="text-gray-600 mt-2">{currentProject.description}</p>
              <div className="mt-4 flex gap-6 text-sm text-gray-600">
                <span>Documents: <strong>{documents.length}</strong></span>
                <span>Extractions: <strong>{currentProject.extraction_count}</strong></span>
                <span>Status: <span className="font-semibold">{currentProject.status}</span></span>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={loadProject}
                className="flex items-center gap-2 bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300"
              >
                <RefreshCw size={18} />
                Refresh
              </button>
              <button
                onClick={handleDeleteProject}
                className="flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
              >
                <Trash2 size={18} />
                Delete
              </button>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-1 mb-8 border-b border-gray-200 overflow-x-auto">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => {
                setActiveTab(id);
                if (id === 'table') loadComparisonTable();
              }}
              className={`flex items-center gap-2 px-4 py-3 font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div>
          {activeTab === 'documents' && (
            <div className="space-y-6">
              <DocumentUploadSection
                onUpload={handleDocumentUpload}
                isLoading={isLoading}
              />

              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold mb-4">Uploaded Documents</h2>
                {documents.length === 0 ? (
                  <p className="text-gray-500">No documents uploaded yet</p>
                ) : (
                  <div className="space-y-3">
                    {documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="flex justify-between items-center p-4 bg-gray-50 rounded-lg"
                      >
                        <div>
                          <p className="font-medium text-gray-900">{doc.filename}</p>
                          <p className="text-sm text-gray-600">
                            {(doc.file_size / 1024).toFixed(2)} KB | {doc.file_type.toUpperCase()}
                          </p>
                        </div>
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-medium ${
                            doc.status === 'INDEXED'
                              ? 'bg-green-100 text-green-800'
                              : doc.status === 'EXTRACTED'
                                ? 'bg-blue-100 text-blue-800'
                                : doc.status === 'ERROR'
                                  ? 'bg-red-100 text-red-800'
                                  : 'bg-yellow-100 text-yellow-800'
                          }`}
                        >
                          {doc.status}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold mb-4">Extract Fields</h2>
                <p className="text-gray-600 mb-4">
                  Extract key fields from all documents using the configured field template.
                </p>
                <button
                  onClick={handleExtractFields}
                  disabled={extracting || documents.length === 0}
                  className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400"
                >
                  {extracting ? 'Extracting...' : 'Start Extraction'}
                </button>
                {extracting && (
                  <p className="text-sm text-blue-600 mt-2 animate-pulse">
                    Extraction in progress. This may take a few minutes...
                  </p>
                )}
              </div>
            </div>
          )}

          {activeTab === 'table' && tableData && (
            <ComparisonTableView data={tableData} projectId={projectId!} />
          )}

          {activeTab === 'diff' && (
            <DiffHighlightView projectId={projectId!} />
          )}

          {activeTab === 'review' && (
            <ReviewPanel projectId={projectId!} />
          )}

          {activeTab === 'annotations' && (
            <AnnotationPanel projectId={projectId!} />
          )}

          {activeTab === 'evaluation' && (
            <EvaluationReport projectId={projectId!} />
          )}

          {activeTab === 'settings' && (
            <FieldTemplateManager projectId={projectId!} />
          )}
        </div>
      </div>
    </div>
  );
};
