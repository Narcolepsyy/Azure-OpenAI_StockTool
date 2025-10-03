import React, { useState, useEffect, useCallback } from 'react';
import { X, ChevronDown, ChevronUp, RefreshCw, ExternalLink } from 'lucide-react';
import { getToken } from '../../lib/api';

interface SummaryItem {
  title: string;
  content: string;
  source: string;
  url: string;
}

interface SummarySection {
  section_title: string;
  items: SummaryItem[];
  source_count: number;
}

interface MarketSummaryData {
  sections: SummarySection[];
  last_updated: string;
  total_articles?: number;
  error?: string;
}

interface MarketSummaryProps {
  isOpen: boolean;
  onClose: () => void;
}

const MarketSummary: React.FC<MarketSummaryProps> = ({ isOpen, onClose }) => {
  const [data, setData] = useState<MarketSummaryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  const fetchMarketSummary = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const token = getToken();
      if (!token) {
        throw new Error('Not authenticated');
      }

      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
      const response = await fetch(`${apiBase}/dashboard/market/summary`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      setData(result);

      // Auto-expand first section if none expanded
      if (result.sections && result.sections.length > 0 && expandedSections.size === 0) {
        setExpandedSections(new Set([result.sections[0].section_title]));
      }
    } catch (err) {
      console.error('Error fetching market summary:', err);
      setError(err instanceof Error ? err.message : 'Failed to load market summary');
    } finally {
      setLoading(false);
    }
  }, [expandedSections.size]);

  useEffect(() => {
    if (isOpen && !data) {
      fetchMarketSummary();
    }
  }, [isOpen, data, fetchMarketSummary]);

  const toggleSection = (sectionTitle: string) => {
    setExpandedSections(prev => {
      const newSet = new Set(prev);
      if (newSet.has(sectionTitle)) {
        newSet.delete(sectionTitle);
      } else {
        newSet.add(sectionTitle);
      }
      return newSet;
    });
  };

  const formatTimeAgo = (isoString: string) => {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins} minute${diffMins > 1 ? 's' : ''} ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-4xl max-h-[85vh] mx-4 bg-[#1a1a1a] rounded-xl shadow-2xl border border-gray-800 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800 shrink-0">
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-semibold text-white">Market Summary</h2>
            {data?.last_updated && (
              <span className="text-sm text-gray-400">
                Updated {formatTimeAgo(data.last_updated)}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={fetchMarketSummary}
              disabled={loading}
              className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-gray-200 transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-gray-200 transition-colors"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading && !data && (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
            </div>
          )}

          {error && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-4 py-3 text-red-400">
              {error}
            </div>
          )}

          {data && !data.sections.length && (
            <div className="text-center py-12 text-gray-400">
              No market summary available at this time.
            </div>
          )}

          {data && data.sections.length > 0 && (
            <div className="space-y-4">
              {data.sections.map((section, idx) => (
                <div
                  key={idx}
                  className="rounded-lg bg-[#222] border border-gray-800 overflow-hidden hover:border-gray-700 transition-colors"
                >
                  {/* Section Header */}
                  <button
                    onClick={() => toggleSection(section.section_title)}
                    className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-800/50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <h3 className="font-semibold text-white text-base">
                        {section.section_title}
                      </h3>
                      <span className="text-xs text-gray-500">
                        {section.source_count} {section.source_count === 1 ? 'Source' : 'Sources'}
                      </span>
                    </div>
                    {expandedSections.has(section.section_title) ? (
                      <ChevronUp className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    )}
                  </button>

                  {/* Section Content */}
                  {expandedSections.has(section.section_title) && (
                    <div className="px-4 pb-4 space-y-4">
                      {section.items.map((item, itemIdx) => (
                        <div key={itemIdx} className="space-y-2">
                          <div className="flex items-start justify-between gap-2">
                            <h4 className="font-medium text-white text-sm leading-snug flex-1">
                              {item.title}
                            </h4>
                            {item.url && (
                              <a
                                href={item.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-gray-400 hover:text-blue-400 transition-colors shrink-0"
                                title="Read full article"
                              >
                                <ExternalLink className="w-4 h-4" />
                              </a>
                            )}
                          </div>
                          <p className="text-gray-300 text-sm leading-relaxed">
                            {item.content}
                          </p>
                          {item.source && (
                            <p className="text-xs text-gray-500 flex items-center gap-1">
                              <span className="w-1 h-1 rounded-full bg-gray-600"></span>
                              {item.source}
                            </p>
                          )}
                          {itemIdx < section.items.length - 1 && (
                            <div className="pt-3 border-b border-gray-800"></div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        {data && data.total_articles && (
          <div className="px-6 py-3 border-t border-gray-800 text-center shrink-0">
            <p className="text-xs text-gray-500">
              Based on {data.total_articles} recent articles
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default MarketSummary;
