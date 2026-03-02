import React from 'react';
import { Link } from 'react-router-dom';

interface Tool {
  id: string;
  name: string;
  description: string;
}

interface ToolCardProps {
  tool: Tool;
}

const ToolCard: React.FC<ToolCardProps> = ({ tool }) => {
  return (
    <Link to={`/tools/${tool.id}`} className="block p-6 bg-white rounded-lg shadow hover:shadow-lg transition border border-gray-200">
      <h2 className="text-xl font-semibold mb-2">{tool.name}</h2>
      <p className="text-gray-600">{tool.description}</p>
    </Link>
  );
};

export default ToolCard;