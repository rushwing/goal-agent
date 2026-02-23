import { AxiosInstance } from "axios";

export function registerAdminTools(client: AxiosInstance) {
  return {
    add_pupil: async (args: {
      name: string;
      display_name: string;
      grade: string;
      telegram_chat_id: number;
      parent_id?: number;
    }) => {
      const { data } = await client.post("/admin/pupils", args);
      return data;
    },

    update_pupil: async (args: {
      pupil_id: number;
      name?: string;
      display_name?: string;
      grade?: string;
      telegram_chat_id?: number;
      is_active?: boolean;
    }) => {
      const { pupil_id, ...body } = args;
      const { data } = await client.patch(`/admin/pupils/${pupil_id}`, body);
      return data;
    },

    remove_pupil: async (args: { pupil_id: number }) => {
      const { data } = await client.delete(`/admin/pupils/${args.pupil_id}`);
      return data;
    },

    list_pupils: async () => {
      const { data } = await client.get("/admin/pupils");
      return data;
    },

    add_parent: async (args: {
      name: string;
      telegram_chat_id: number;
      is_admin?: boolean;
    }) => {
      const { data } = await client.post("/admin/parents", args);
      return data;
    },

    update_parent: async (args: {
      parent_id: number;
      name?: string;
      telegram_chat_id?: number;
      is_admin?: boolean;
    }) => {
      const { parent_id, ...body } = args;
      const { data } = await client.patch(`/admin/parents/${parent_id}`, body);
      return data;
    },

    remove_parent: async (args: { parent_id: number }) => {
      const { data } = await client.delete(`/admin/parents/${args.parent_id}`);
      return data;
    },

    list_parents: async () => {
      const { data } = await client.get("/admin/parents");
      return data;
    },
  };
}
