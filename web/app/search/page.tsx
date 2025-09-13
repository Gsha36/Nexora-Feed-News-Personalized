'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { searchArticles, getStats, Article, Stats, SearchParams } from '../../lib/api';
import ArticleCard from '../../components/ArticleCard';
import SearchBar from '../../components/SearchBar';
import Filters from '../../components/Filters';

export default function SearchPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalResults, setTotalResults] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTime, setSearchTime] = useState(0);

  // Filters state
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>([]);
  const [selectedSentiment, setSelectedSentiment] = useState<string>();

  const router = useRouter();
  const searchParams = useSearchParams();
  const query = searchParams.get('q') || '';

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const statsData = await getStats();
        setStats(statsData);
      } catch (err) {
        console.error('Error fetching stats:', err);
      }
    };

    fetchStats();
  }, []);

  useEffect(() => {
    if (query) {
      performSearch(query, 1);
    }
  }, [query, selectedSources, selectedLanguages, selectedSentiment]);

  const performSearch = async (searchQuery: string, page: number = 1) => {
    if (!searchQuery.trim()) return;

    try {
      setLoading(true);
      setError(null);

      const params: SearchParams = {
        query: searchQuery,
        page,
        size: 20,
      };

      if (selectedSources.length > 0) params.sources = selectedSources;
      if (selectedLanguages.length > 0) params.languages = selectedLanguages;
      if (selectedSentiment) params.sentiment = selectedSentiment as any;

      const response = await searchArticles(params);
      
      setArticles(response.articles);
      setTotalResults(response.total);
      setCurrentPage(page);
      setSearchTime(response.took);
    } catch (err) {
      setError('Search failed. Please try again.');
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (newQuery: string) => {
    router.push(`/search?q=${encodeURIComponent(newQuery)}`);
  };

  const handlePageChange = (page: number) => {
    performSearch(query, page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const clearFilters = () => {
    setSelectedSources([]);
    setSelectedLanguages([]);
    setSelectedSentiment(undefined);
  };

  const totalPages = Math.ceil(totalResults / 20);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between mb-6">
            <h1 
              className="text-2xl font-bold text-gray-900 cursor-pointer"
              onClick={() => router.push('/')}
            >
              Nexora News
            </h1>
          </div>
          
          <div className="max-w-2xl">
            <SearchBar onSearch={handleSearch} initialValue={query} />
          </div>

          {query && (
            <div className="mt-4 text-sm text-gray-600">
              {loading ? (
                'Searching...'
              ) : (
                `Found ${totalResults.toLocaleString()} results for "${query}" in ${searchTime}ms`
              )}
            </div>
          )}
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Filters Sidebar */}
          <div className="lg:col-span-1">
            {stats && (
              <Filters
                sources={stats.sources.map(s => ({ value: s.name, label: s.name, count: s.count }))}
                languages={stats.languages.map(l => ({ value: l.name, label: l.name.toUpperCase(), count: l.count }))}
                sentiments={stats.sentiments.map(s => ({ 
                  value: s.name, 
                  label: s.name.charAt(0).toUpperCase() + s.name.slice(1), 
                  count: s.count 
                }))}
                selectedSources={selectedSources}
                selectedLanguages={selectedLanguages}
                selectedSentiment={selectedSentiment}
                onSourcesChange={setSelectedSources}
                onLanguagesChange={setSelectedLanguages}
                onSentimentChange={setSelectedSentiment}
                onClearFilters={clearFilters}
              />
            )}
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            {loading && (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500"></div>
                <span className="ml-2 text-gray-600">Searching...</span>
              </div>
            )}

            {error && (
              <div className="text-center py-12">
                <p className="text-red-600 mb-4">{error}</p>
                <button
                  onClick={() => performSearch(query, currentPage)}
                  className="btn btn-primary"
                >
                  Try Again
                </button>
              </div>
            )}

            {!loading && !error && articles.length === 0 && query && (
              <div className="text-center py-12">
                <p className="text-gray-500">No articles found for your search.</p>
                <p className="text-sm text-gray-400 mt-2">Try adjusting your filters or search terms.</p>
              </div>
            )}

            {!loading && !error && articles.length > 0 && (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                  {articles.map((article) => (
                    <ArticleCard key={article.id} article={article} />
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-center space-x-2">
                    <button
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                      className="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Previous
                    </button>
                    
                    <div className="flex space-x-1">
                      {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                        const page = i + 1;
                        return (
                          <button
                            key={page}
                            onClick={() => handlePageChange(page)}
                            className={`px-3 py-2 rounded-md text-sm font-medium ${
                              page === currentPage
                                ? 'bg-primary-500 text-white'
                                : 'bg-white text-gray-700 hover:bg-gray-50'
                            }`}
                          >
                            {page}
                          </button>
                        );
                      })}
                    </div>

                    <button
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                      className="btn btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Next
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}