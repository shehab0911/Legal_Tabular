import axios, { AxiosInstance } from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

// For sandbox environments, detect if we need the direct backend URL
const getBaseUrl = () => {
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname;
    // If accessed through sandbox proxy, use direct backend URL
    if (hostname.includes("sandbox") && hostname.startsWith("5173")) {
      return hostname.replace("5173", "8000").replace(/^/, "https://");
    }
  }
  return API_BASE_URL;
};

const apiClient: AxiosInstance = axios.create({
  baseURL: getBaseUrl(),
  headers: {
    "Content-Type": "application/json",
  },
});

// ==================== PROJECT APIS ====================

export const projectAPI = {
  createProject: async (
    name: string,
    description?: string,
    fieldTemplateId?: string,
  ) => {
    const response = await apiClient.post("/projects", {
      name,
      description,
      field_template_id: fieldTemplateId,
    });
    return response.data;
  },

  getProject: async (projectId: string) => {
    const response = await apiClient.get(`/projects/${projectId}`);
    return response.data;
  },

  listProjects: async (skip = 0, limit = 100) => {
    const response = await apiClient.get("/projects", {
      params: { skip, limit },
    });
    return response.data;
  },

  updateProject: async (
    projectId: string,
    name?: string,
    description?: string,
    fieldTemplateId?: string,
  ) => {
    const response = await apiClient.put(`/projects/${projectId}`, {
      name,
      description,
      field_template_id: fieldTemplateId,
    });
    return response.data;
  },

  deleteProject: async (projectId: string) => {
    const response = await apiClient.delete(`/projects/${projectId}`);
    return response.data;
  },
};

// ==================== DOCUMENT APIS ====================

export const documentAPI = {
  uploadDocument: async (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await apiClient.post(
      `/projects/${projectId}/documents/upload`,
      formData,
      {
        headers: { "Content-Type": "multipart/form-data" },
      },
    );
    return response.data;
  },

  listDocuments: async (projectId: string) => {
    const response = await apiClient.get(`/projects/${projectId}/documents`);
    return response.data;
  },
};

// ==================== FIELD TEMPLATE APIS ====================

export const fieldTemplateAPI = {
  createTemplate: async (name: string, description: string, fields: any[]) => {
    const response = await apiClient.post("/field-templates", {
      name,
      description,
      fields,
    });
    return response.data;
  },

  listTemplates: async () => {
    const response = await apiClient.get("/field-templates");
    return response.data;
  },

  getTemplate: async (templateId: string) => {
    const response = await apiClient.get(`/field-templates/${templateId}`);
    return response.data;
  },

  updateTemplate: async (
    templateId: string,
    name: string,
    description: string,
    fields: any[],
  ) => {
    const response = await apiClient.put(`/field-templates/${templateId}`, {
      name,
      description,
      fields,
    });
    return response.data;
  },
};

// ==================== EXTRACTION APIS ====================

export const extractionAPI = {
  extractFields: async (projectId: string, documentId?: string) => {
    const response = await apiClient.post(`/projects/${projectId}/extract`, {
      document_id: documentId,
    });
    return response.data;
  },
};

// ==================== EXTRACTION LIST API ====================

export const extractionListAPI = {
  listExtractions: async (projectId: string) => {
    const response = await apiClient.get(`/projects/${projectId}/extractions`);
    return response.data;
  },
};

// ==================== REVIEW APIS ====================

export const reviewAPI = {
  reviewExtraction: async (
    extractionId: string,
    status: string,
    manualValue?: string,
    notes?: string,
    reviewedBy?: string,
  ) => {
    const response = await apiClient.put(
      `/extractions/${extractionId}/review`,
      {
        status,
        manual_value: manualValue,
        reviewer_notes: notes,
        reviewed_by: reviewedBy,
      },
    );
    return response.data;
  },

  getPendingReviews: async (projectId: string) => {
    const response = await apiClient.get(
      `/projects/${projectId}/reviews/pending`,
    );
    return response.data;
  },
};

// ==================== COMPARISON TABLE APIS ====================

export const comparisonAPI = {
  getTable: async (projectId: string) => {
    const response = await apiClient.get(`/projects/${projectId}/table`);
    return response.data;
  },

  exportCSV: async (projectId: string) => {
    const response = await apiClient.post(
      `/projects/${projectId}/table/export-csv`,
    );
    return response.data;
  },

  exportExcel: async (projectId: string) => {
    const response = await apiClient.post(
      `/projects/${projectId}/table/export-excel`,
    );
    return response.data;
  },
};

// ==================== DIFF APIS ====================

export const diffAPI = {
  getDiff: async (projectId: string) => {
    const response = await apiClient.get(`/projects/${projectId}/diff`);
    return response.data;
  },
};

// ==================== ANNOTATION APIS ====================

export const annotationAPI = {
  createAnnotation: async (
    extractionId: string,
    commentText: string,
    annotatedBy: string = "anonymous",
  ) => {
    const response = await apiClient.post("/annotations", {
      extraction_id: extractionId,
      comment_text: commentText,
      annotated_by: annotatedBy,
    });
    return response.data;
  },

  listExtractionAnnotations: async (extractionId: string) => {
    const response = await apiClient.get(
      `/extractions/${extractionId}/annotations`,
    );
    return response.data;
  },

  listProjectAnnotations: async (projectId: string) => {
    const response = await apiClient.get(
      `/projects/${projectId}/annotations`,
    );
    return response.data;
  },

  updateAnnotation: async (annotationId: string, commentText: string) => {
    const response = await apiClient.put(`/annotations/${annotationId}`, {
      comment_text: commentText,
    });
    return response.data;
  },

  deleteAnnotation: async (annotationId: string) => {
    const response = await apiClient.delete(`/annotations/${annotationId}`);
    return response.data;
  },
};

// ==================== RE-EXTRACTION APIS ====================

export const reExtractionAPI = {
  reExtract: async (projectId: string) => {
    const response = await apiClient.post(
      `/projects/${projectId}/re-extract`,
    );
    return response.data;
  },
};

// ==================== EVALUATION APIS ====================

export const evaluationAPI = {
  evaluateProject: async (projectId: string, evaluationData: any) => {
    const response = await apiClient.post(
      `/projects/${projectId}/evaluate`,
      evaluationData,
    );
    return response.data;
  },

  getReport: async (projectId: string) => {
    const response = await apiClient.get(
      `/projects/${projectId}/evaluation-report`,
    );
    return response.data;
  },
};

// ==================== TASK APIS ====================

export const taskAPI = {
  getStatus: async (taskId: string) => {
    const response = await apiClient.get(`/tasks/${taskId}`);
    return response.data;
  },
};

export default apiClient;
