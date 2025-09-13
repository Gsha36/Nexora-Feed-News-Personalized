import { useState } from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';

interface FilterOption {
  value: string;
  label: string;
  count?: number;
}

interface FiltersProps {
  sources: FilterOption[];
  languages: FilterOption[];
  sentiments: FilterOption[];
  selectedSources: string[];
  selectedLanguages: string[];
  selectedSentiment?: string;
  onSourcesChange: (sources: string[]) => void;
  onLanguagesChange: (languages: string[]) => void;
  onSentimentChange: (sentiment?: string) => void;
  onClearFilters: () => void;
}

export default function Filters({
  sources,
  languages,
  sentiments,
  selectedSources,
  selectedLanguages,
  selectedSentiment,
  onSourcesChange,
  onLanguagesChange,
  onSentimentChange,
  onClearFilters,
}: FiltersProps) {
  const [showSources, setShowSources] = useState(false);
  const [showLanguages, setShowLanguages] = useState(false);

  const handleSourceToggle = (source: string) => {
    if (selectedSources.includes(source)) {
      onSourcesChange(selectedSources.filter(s => s !== source));
    } else {
      onSourcesChange([...selectedSources, source]);
    }
  };

  const handleLanguageToggle = (language: string) => {
    if (selectedLanguages.includes(language)) {
      onLanguagesChange(selectedLanguages.filter(l => l !== language));
    } else {
      onLanguagesChange([...selectedLanguages, language]);
    }
  };

  const hasActiveFilters = 
    selectedSources.length > 0 || 
    selectedLanguages.length > 0 || 
    selectedSentiment;

  return (
    <div className="bg-white p-4 rounded-lg shadow-md border border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
        {hasActiveFilters && (
          <button
            onClick={onClearFilters}
            className="text-sm text-primary-600 hover:text-primary-700"
          >
            Clear all
          </button>
        )}
      </div>

      {/* Sources Filter */}
      <div className="mb-4">
        <button
          onClick={() => setShowSources(!showSources)}
          className="flex items-center justify-between w-full text-left font-medium text-gray-700 mb-2"
        >
          Sources ({selectedSources.length})
          <ChevronDownIcon 
            className={`h-4 w-4 transform transition-transform ${showSources ? 'rotate-180' : ''}`} 
          />
        </button>
        {showSources && (
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {sources.map((source) => (
              <label key={source.value} className="flex items-center">
                <input
                  type="checkbox"
                  checked={selectedSources.includes(source.value)}
                  onChange={() => handleSourceToggle(source.value)}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="ml-2 text-sm text-gray-600">
                  {source.label} {source.count && `(${source.count})`}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Languages Filter */}
      <div className="mb-4">
        <button
          onClick={() => setShowLanguages(!showLanguages)}
          className="flex items-center justify-between w-full text-left font-medium text-gray-700 mb-2"
        >
          Languages ({selectedLanguages.length})
          <ChevronDownIcon 
            className={`h-4 w-4 transform transition-transform ${showLanguages ? 'rotate-180' : ''}`} 
          />
        </button>
        {showLanguages && (
          <div className="space-y-2">
            {languages.map((language) => (
              <label key={language.value} className="flex items-center">
                <input
                  type="checkbox"
                  checked={selectedLanguages.includes(language.value)}
                  onChange={() => handleLanguageToggle(language.value)}
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <span className="ml-2 text-sm text-gray-600">
                  {language.label} {language.count && `(${language.count})`}
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Sentiment Filter */}
      <div>
        <label className="block font-medium text-gray-700 mb-2">
          Sentiment
        </label>
        <div className="space-y-2">
          <label className="flex items-center">
            <input
              type="radio"
              name="sentiment"
              checked={!selectedSentiment}
              onChange={() => onSentimentChange(undefined)}
              className="text-primary-600 focus:ring-primary-500"
            />
            <span className="ml-2 text-sm text-gray-600">All</span>
          </label>
          {sentiments.map((sentiment) => (
            <label key={sentiment.value} className="flex items-center">
              <input
                type="radio"
                name="sentiment"
                checked={selectedSentiment === sentiment.value}
                onChange={() => onSentimentChange(sentiment.value)}
                className="text-primary-600 focus:ring-primary-500"
              />
              <span className="ml-2 text-sm text-gray-600">
                {sentiment.label} {sentiment.count && `(${sentiment.count})`}
              </span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}