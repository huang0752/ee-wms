import { request, NO_AUTH_FLAG } from "@utils";
import type { AssemblySummary } from "@/config/assembly/default";

const API_PATH = "/system/config";

export interface PublicConfigInfo {
  assembly: AssemblySummary;
}

const SystemConfigAPI = {
  getPublicConfigInfo() {
    return request<ApiResponse<PublicConfigInfo>>({
      url: `${API_PATH}/info`,
      method: "get",
      headers: {
        Authorization: NO_AUTH_FLAG,
      },
    });
  },
};

export default SystemConfigAPI;
