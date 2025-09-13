import Link from 'next/link';
import { formatDistanceToNow } from 'date-fns';
import { Article } from '../lib/api';

interface ArticleCardProps {
  article: Article;
}

export default function ArticleCard({ article }: ArticleCardProps) {
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
    <div className="card hover:shadow-lg transition-shadow">
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-primary-600">
            {article.source}
          </span>
          <span className="text-xs text-gray-500">
            {formatDistanceToNow(new Date(article.published_at), { addSuffix: true })}
          </span>
        </div>
        <span
          className={`px-2 py-1 rounded-full text-xs font-medium ${getSentimentColor(
            article.sentiment
          )}`}
        >
          {article.sentiment}
        </span>
      </div>

      <Link href={`/article/${article.id}`}>
        <h3 className="text-lg font-semibold text-gray-900 mb-2 hover:text-primary-600 cursor-pointer">
          {article.title}
        </h3>
      </Link>

      <p className="text-gray-600 text-sm mb-3 line-clamp-3">
        {article.summary}
      </p>

      {article.topics.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {article.topics.slice(0, 3).map((topic, index) => (
            <span
              key={index}
              className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-md"
            >
              {topic}
            </span>
          ))}
          {article.topics.length > 3 && (
            <span className="px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-md">
              +{article.topics.length - 3} more
            </span>
          )}
        </div>
      )}

      <div className="flex justify-between items-center text-xs text-gray-500">
        <span>{article.word_count} words</span>
        {article.author && <span>By {article.author}</span>}
        <span className="uppercase">{article.language}</span>
      </div>
    </div>
  );
}