import React, { useEffect, useState } from "react";
import { List, Plus, Edit, Save, X, Trash2, RotateCcw } from "lucide-react";
import toast from "react-hot-toast";
import { fieldTemplateAPI, projectAPI, reExtractionAPI, taskAPI } from "../services/api";

interface FieldTemplateManagerProps {
  projectId: string;
}

interface FieldDef {
  name: string;
  display_name: string;
  field_type: string;
  description: string;
  required: boolean;
  validation_rules?: Record<string, any> | null;
  normalization_rules?: Record<string, any> | null;
  examples?: string[] | null;
}

interface Template {
  id: string;
  name: string;
  description?: string;
  version: number;
  fields: FieldDef[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

const FIELD_TYPES = ["TEXT", "DATE", "CURRENCY", "PERCENTAGE", "ENTITY", "BOOLEAN", "MULTI_SELECT", "FREEFORM"];

const DEFAULT_FIELD: FieldDef = {
  name: "",
  display_name: "",
  field_type: "TEXT",
  description: "",
  required: false,
  validation_rules: null,
  normalization_rules: null,
  examples: null,
};

const FieldTemplateManager: React.FC<FieldTemplateManagerProps> = ({ projectId }) => {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [activeTemplate, setActiveTemplate] = useState<Template | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isReExtracting, setIsReExtracting] = useState(false);

  // Edit state
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editFields, setEditFields] = useState<FieldDef[]>([]);

  // Create new template
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");

  // Current project template
  const [projectTemplateId, setProjectTemplateId] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [projectId]);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [tmplData, projData] = await Promise.all([
        fieldTemplateAPI.listTemplates(),
        projectAPI.getProject(projectId),
      ]);
      setTemplates(tmplData.templates || []);
      setProjectTemplateId(projData.field_template_id || null);

      // Load active template if project has one
      if (projData.field_template_id) {
        const tmpl = await fieldTemplateAPI.getTemplate(projData.field_template_id);
        setActiveTemplate(tmpl);
      }
    } catch (error) {
      toast.error("Failed to load template data");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateTemplate = async () => {
    if (!newName.trim()) {
      toast.error("Template name is required");
      return;
    }
    try {
      const tmpl = await fieldTemplateAPI.createTemplate(newName, newDescription, [
        {
          name: "parties",
          display_name: "Parties",
          field_type: "TEXT",
          description: "The parties involved in the agreement",
          required: true,
        },
        {
          name: "effective_date",
          display_name: "Effective Date",
          field_type: "DATE",
          description: "Effective date of the agreement",
          required: true,
        },
      ]);
      toast.success("Template created");
      setShowCreate(false);
      setNewName("");
      setNewDescription("");
      await loadData();
      // Assign to project
      await projectAPI.updateProject(projectId, undefined, undefined, tmpl.id);
      setProjectTemplateId(tmpl.id);
      setActiveTemplate(tmpl);
    } catch (error) {
      toast.error("Failed to create template");
    }
  };

  const handleAssignTemplate = async (templateId: string) => {
    try {
      await projectAPI.updateProject(projectId, undefined, undefined, templateId);
      setProjectTemplateId(templateId);
      const tmpl = await fieldTemplateAPI.getTemplate(templateId);
      setActiveTemplate(tmpl);
      toast.success("Template assigned to project");
    } catch (error) {
      toast.error("Failed to assign template");
    }
  };

  const startEdit = () => {
    if (!activeTemplate) return;
    setEditName(activeTemplate.name);
    setEditDescription(activeTemplate.description || "");
    setEditFields(JSON.parse(JSON.stringify(activeTemplate.fields || [])));
    setIsEditing(true);
  };

  const cancelEdit = () => {
    setIsEditing(false);
    setEditFields([]);
  };

  const addField = () => {
    setEditFields([...editFields, { ...DEFAULT_FIELD }]);
  };

  const removeField = (index: number) => {
    setEditFields(editFields.filter((_, i) => i !== index));
  };

  const updateField = (index: number, updates: Partial<FieldDef>) => {
    setEditFields(
      editFields.map((f, i) => (i === index ? { ...f, ...updates } : f))
    );
  };

  const handleSaveTemplate = async () => {
    if (!activeTemplate) return;
    // Validate
    for (const field of editFields) {
      if (!field.name.trim() || !field.display_name.trim()) {
        toast.error("All fields must have a name and display name");
        return;
      }
    }
    try {
      const updated = await fieldTemplateAPI.updateTemplate(
        activeTemplate.id,
        editName,
        editDescription,
        editFields
      );
      setActiveTemplate(updated);
      setIsEditing(false);
      toast.success(`Template updated to version ${updated.version}`);
      await loadData();
    } catch (error) {
      toast.error("Failed to save template");
    }
  };

  const handleReExtract = async () => {
    if (!window.confirm("This will delete all existing extractions and re-run extraction with the current template. Continue?")) {
      return;
    }
    setIsReExtracting(true);
    try {
      const result = await reExtractionAPI.reExtract(projectId);
      toast.success("Re-extraction started");
      // Poll task
      const taskId = result.task_id;
      let attempts = 0;
      const maxAttempts = 60;
      const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));
      while (attempts < maxAttempts) {
        const status = await taskAPI.getStatus(taskId);
        if (status.status === "COMPLETED") {
          toast.success("Re-extraction completed");
          break;
        }
        if (status.status === "FAILED") {
          toast.error("Re-extraction failed: " + (status.error_message || "Unknown error"));
          break;
        }
        attempts++;
        await delay(2000);
      }
    } catch (error) {
      toast.error("Failed to start re-extraction");
    } finally {
      setIsReExtracting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-gray-500">Loading template settings...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Template Selection */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-2xl font-semibold text-gray-900">Field Template</h2>
          <div className="flex gap-2">
            <button
              onClick={() => setShowCreate(!showCreate)}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 text-sm"
            >
              <Plus size={16} />
              New Template
            </button>
            {activeTemplate && (
              <button
                onClick={handleReExtract}
                disabled={isReExtracting}
                className="flex items-center gap-2 bg-orange-600 text-white px-4 py-2 rounded-lg hover:bg-orange-700 text-sm disabled:bg-gray-400"
              >
                <RotateCcw size={16} />
                {isReExtracting ? "Re-extracting..." : "Re-Extract All"}
              </button>
            )}
          </div>
        </div>

        {/* Current Template Info */}
        {activeTemplate ? (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <div className="flex justify-between items-start">
              <div>
                <p className="font-semibold text-blue-900">{activeTemplate.name}</p>
                <p className="text-sm text-blue-700">
                  Version {activeTemplate.version} | {activeTemplate.fields?.length || 0} fields
                </p>
                {activeTemplate.description && (
                  <p className="text-sm text-blue-600 mt-1">{activeTemplate.description}</p>
                )}
              </div>
              <button
                onClick={startEdit}
                className="flex items-center gap-1 bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 text-sm"
              >
                <Edit size={14} />
                Edit
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
            <p className="text-yellow-800">No template assigned. Select or create one below.</p>
          </div>
        )}

        {/* Available Templates */}
        {templates.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">Available Templates</p>
            <div className="space-y-2">
              {templates.map((t: any) => (
                <div
                  key={t.id}
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    t.id === projectTemplateId
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 hover:bg-gray-50"
                  }`}
                >
                  <div>
                    <p className="font-medium text-gray-900">{t.name}</p>
                    <p className="text-xs text-gray-500">
                      v{t.version} | {t.fields_count} fields
                    </p>
                  </div>
                  {t.id !== projectTemplateId && (
                    <button
                      onClick={() => handleAssignTemplate(t.id)}
                      className="bg-gray-200 text-gray-800 px-3 py-1 rounded text-sm hover:bg-gray-300"
                    >
                      Use This
                    </button>
                  )}
                  {t.id === projectTemplateId && (
                    <span className="text-xs font-medium text-blue-600 bg-blue-100 px-2 py-1 rounded">
                      Active
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Create New Template Form */}
      {showCreate && (
        <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-green-500">
          <h3 className="font-semibold text-gray-900 mb-4">Create New Template</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                placeholder="E.g., Contract Review Template"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                rows={2}
                placeholder="Optional description..."
              />
            </div>
            <div className="flex gap-2">
              <button onClick={handleCreateTemplate} className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700">
                Create
              </button>
              <button
                onClick={() => { setShowCreate(false); setNewName(""); setNewDescription(""); }}
                className="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Fields */}
      {isEditing && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xl font-semibold text-gray-900">Edit Template Fields</h3>
            <div className="flex gap-2">
              <button
                onClick={addField}
                className="flex items-center gap-1 bg-green-600 text-white px-3 py-2 rounded hover:bg-green-700 text-sm"
              >
                <Plus size={16} />
                Add Field
              </button>
              <button
                onClick={handleSaveTemplate}
                className="flex items-center gap-1 bg-blue-600 text-white px-3 py-2 rounded hover:bg-blue-700 text-sm"
              >
                <Save size={16} />
                Save Template
              </button>
              <button
                onClick={cancelEdit}
                className="flex items-center gap-1 bg-gray-200 text-gray-800 px-3 py-2 rounded hover:bg-gray-300 text-sm"
              >
                <X size={16} />
                Cancel
              </button>
            </div>
          </div>

          <div className="space-y-3 mb-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Template Name</label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <input
                  type="text"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                />
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100">
                  <th className="px-3 py-2 text-left">#</th>
                  <th className="px-3 py-2 text-left">Name (key)</th>
                  <th className="px-3 py-2 text-left">Display Name</th>
                  <th className="px-3 py-2 text-left">Type</th>
                  <th className="px-3 py-2 text-left">Description</th>
                  <th className="px-3 py-2 text-center">Required</th>
                  <th className="px-3 py-2"></th>
                </tr>
              </thead>
              <tbody>
                {editFields.map((field, idx) => (
                  <tr key={idx} className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                    <td className="px-3 py-2 text-gray-500">{idx + 1}</td>
                    <td className="px-3 py-2">
                      <input
                        type="text"
                        value={field.name}
                        onChange={(e) => updateField(idx, { name: e.target.value })}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                        placeholder="field_key"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="text"
                        value={field.display_name}
                        onChange={(e) => updateField(idx, { display_name: e.target.value })}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                        placeholder="Display Name"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <select
                        value={field.field_type}
                        onChange={(e) => updateField(idx, { field_type: e.target.value })}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                      >
                        {FIELD_TYPES.map((t) => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="text"
                        value={field.description}
                        onChange={(e) => updateField(idx, { description: e.target.value })}
                        className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
                        placeholder="Description"
                      />
                    </td>
                    <td className="px-3 py-2 text-center">
                      <input
                        type="checkbox"
                        checked={field.required}
                        onChange={(e) => updateField(idx, { required: e.target.checked })}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <button
                        onClick={() => removeField(idx)}
                        className="text-red-500 hover:text-red-700"
                        title="Remove field"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {editFields.length === 0 && (
            <p className="text-center text-gray-500 py-4">No fields. Click "Add Field" to begin.</p>
          )}
        </div>
      )}

      {/* Current Fields (Read-only) */}
      {!isEditing && activeTemplate && activeTemplate.fields && activeTemplate.fields.length > 0 && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-4">
            Current Fields ({activeTemplate.fields.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-100">
                  <th className="px-3 py-2 text-left">#</th>
                  <th className="px-3 py-2 text-left">Name</th>
                  <th className="px-3 py-2 text-left">Type</th>
                  <th className="px-3 py-2 text-left">Description</th>
                  <th className="px-3 py-2 text-center">Required</th>
                </tr>
              </thead>
              <tbody>
                {activeTemplate.fields.map((field: any, idx: number) => (
                  <tr key={idx} className={idx % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                    <td className="px-3 py-2 text-gray-500">{idx + 1}</td>
                    <td className="px-3 py-2 font-medium text-gray-900">
                      {field.display_name || field.name}
                    </td>
                    <td className="px-3 py-2">
                      <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs">
                        {field.field_type}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-gray-600">{field.description || "-"}</td>
                    <td className="px-3 py-2 text-center">{field.required ? "Yes" : "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default FieldTemplateManager;
