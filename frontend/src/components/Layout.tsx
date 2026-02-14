import React from "react";
import { Outlet, Link } from "react-router-dom";
import { FileText } from "lucide-react";

const Layout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <Link to="/projects" className="flex items-center gap-3">
              <FileText size={32} className="text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Legal Tabular Review
                </h1>
                <p className="text-sm text-gray-600">
                  Extract & Compare Legal Documents
                </p>
              </div>
            </Link>
            <nav className="flex gap-6">
              <Link
                to="/projects"
                className="text-gray-600 hover:text-gray-900 font-medium"
              >
                Projects
              </Link>
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-600 hover:text-gray-900 font-medium"
              >
                Docs
              </a>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main>
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <p className="text-center text-gray-600">
            Legal Tabular Review System v1.0.0 | Built for production-grade
            document analysis
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
