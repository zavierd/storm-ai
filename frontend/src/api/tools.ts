import { toolConfigs, type ToolConfig } from '../config/toolConfigs';

export const fetchTools = async (): Promise<ToolConfig[]> => {
  return toolConfigs;
};
