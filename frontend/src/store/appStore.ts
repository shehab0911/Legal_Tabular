import { create } from "zustand";

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
  document_count: number;
  extraction_count: number;
}

export interface Document {
  id: string;
  project_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  created_at: string;
}

export interface ExtractionResult {
  id: string;
  field_name: string;
  extracted_value?: string;
  normalized_value?: string;
  confidence_score: number;
  status: string;
  citations: Citation[];
}

export interface Citation {
  citation_text: string;
  page_number?: number;
  section_title?: string;
  relevance_score: number;
}

export interface ReviewState {
  id: string;
  extraction_id: string;
  status: string;
  ai_value?: string;
  manual_value?: string;
  confidence_score: number;
}

export interface TableRow {
  field_name: string;
  field_type: string;
  document_results: Record<string, any>;
}

export interface AppState {
  // Projects
  currentProject: Project | null;
  projects: Project[];
  setCurrentProject: (project: Project) => void;
  setProjects: (projects: Project[]) => void;

  // Documents
  documents: Document[];
  setDocuments: (documents: Document[]) => void;

  // Extractions
  extractions: ExtractionResult[];
  setExtractions: (extractions: ExtractionResult[]) => void;

  // Reviews
  reviews: ReviewState[];
  setReviews: (reviews: ReviewState[]) => void;

  // Table
  tableRows: TableRow[];
  setTableRows: (rows: TableRow[]) => void;

  // UI State
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;

  // Tasks
  activeTasks: Record<string, any>;
  setActiveTasks: (tasks: Record<string, any>) => void;
}

export const useStore = create<AppState>((set) => ({
  currentProject: null,
  projects: [],
  documents: [],
  extractions: [],
  reviews: [],
  tableRows: [],
  isLoading: false,
  error: null,
  activeTab: "overview",
  activeTasks: {},

  setCurrentProject: (project) => set({ currentProject: project }),
  setProjects: (projects) => set({ projects }),
  setDocuments: (documents) => set({ documents }),
  setExtractions: (extractions) => set({ extractions }),
  setReviews: (reviews) => set({ reviews }),
  setTableRows: (rows) => set({ tableRows: rows }),
  setIsLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  setActiveTasks: (tasks) => set({ activeTasks: tasks }),
}));
