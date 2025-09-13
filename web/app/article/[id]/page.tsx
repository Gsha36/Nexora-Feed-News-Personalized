'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { getArticle, Article } from '../../../lib/api';
import { formatDistanceToNow, format } from 'date-fns';
import { ArrowLeftIcon, ArrowTopRightOnSquareIcon } from '@heroicons/react/24/outline';

interface PageProps {
  params: {
    id: string;
  };
}

export default function ArticlePage({ params }: PageProps) {
  const [article, setArticle] = useState<Article | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchArticle = async () => {
      try {
        setLoading(true);
        const articleData = await getArticle(params.id);
        setArticle(articleData);
      } catch (err) {
        setError('Article not found or failed to load.');
        console.error('Error fetching article:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchArticle();
  }, [params.id]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading article...</p>
        </div>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={() => router.back()}
            className="btn btn-primary"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return 'text-green-600 bg-green-100';
      case 'negative':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <button
            onClick={() => router.back()}
            className="flex items-center text-primary-600 hover:text-primary-700 mb-4"
          >
            <ArrowLeftIcon className="h-4 w-4 mr-1" />
            Back
          </button>
          
          <h1 
            className="text-2xl font-bold text-gray-900 cursor-pointer"
            onClick={() => router.push('/')}
          >
            Nexora News
          </h1>
        </div>
      </header>

      {/* Article Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <article className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
          {/* Article Header */}
          <div className="p-6 sm:p-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center space-x-4">
                <span className="text-lg font-semibold text-primary-600">
                  {article.source}
                </span>
                <span className="text-sm text-gray-500">
                  {formatDistanceToNow(new Date(article.published_at), { addSuffix: true })}
                </span>
              </div>
              
              <div className="flex items-center space-x-2">
                <span
                  className={`px-3 py-1 rounded-full text-sm font-medium ${getSentimentColor(
                    article.sentiment
                  )}`}
                >
                  {article.sentiment}
                </span>
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center text-primary-600 hover:text-primary-700"
                >
                  <ArrowTopRightOnSquareIcon className="h-4 w-4 mr-1" />
                  Original
                </a>
              </div>
            </div>

            <h1 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              {article.title}
            </h1>

            <div className="flex items-center space-x-4 text-sm text-gray-500 mb-6">
              {article.author && <span>By {article.author}</span>}
              <span>{article.word_count} words</span>
              <span className="uppercase">{article.language}</span>
              <span>{format(new Date(article.published_at), 'MMM dd, yyyy')}</span>
            </div>

            {/* Summary */}
            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
              <h2 className="text-lg font-semibold text-blue-900 mb-2">Summary</h2>
              <p className="text-blue-800">{article.summary}</p>
            </div>

            {/* Topics and Entities */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              {article.topics.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Topics</h3>
                  <div className="flex flex-wrap gap-2">
                    {article.topics.map((topic, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-md"
                      >
                        {topic}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {article.entities.length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Entities</h3>
                  <div className="flex flex-wrap gap-2">
                    {article.entities.map((entity, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-green-100 text-green-800 text-sm rounded-md"
                      >
                        {entity}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Article Text */}
            <div className="prose prose-lg max-w-none">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Full Article</h2>
              <div className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                {article.text}
              </div>
            </div>

            {/* Translated Content */}
            {(article.translated_title || article.translated_text) && (
              <div className="mt-8 pt-8 border-t border-gray-200">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Translation</h2>
                {article.translated_title && (
                  <h3 className="text-lg font-medium text-gray-800 mb-2">
                    {article.translated_title}
                  </h3>
                )}
                {article.translated_text && (
                  <div className="text-gray-700 leading-relaxed whitespace-pre-wrap">
                    {article.translated_text}
                  </div>
                )}
              </div>
            )}

            {/* Metadata */}
            <div className="mt-8 pt-8 border-t border-gray-200">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Article Details</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Source:</span>
                  <div className="font-medium">{article.source}</div>
                </div>
                <div>
                  <span className="text-gray-500">Language:</span>
                  <div className="font-medium uppercase">{article.language}</div>
                </div>
                <div>
                  <span className="text-gray-500">Word Count:</span>
                  <div className="font-medium">{article.word_count}</div>
                </div>
                <div>
                  <span className="text-gray-500">Sentiment Score:</span>
                  <div className="font-medium">{article.sentiment_score.toFixed(2)}</div>
                </div>
              </div>
            </div>
          </div>
        </article>
      </main>
    </div>
  );
}