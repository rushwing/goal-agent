import { AxiosInstance } from "axios";

export function registerAdminTools(client: AxiosInstance) {
  return {
    add_go_getter: async (args: {
      name: string;
      display_name: string;
      grade: string;
      telegram_chat_id: number;
      best_pal_id?: number;
    }) => {
      const { data } = await client.post("/admin/go_getters", args);
      return data;
    },

    update_go_getter: async (args: {
      go_getter_id: number;
      name?: string;
      display_name?: string;
      grade?: string;
      telegram_chat_id?: number;
      is_active?: boolean;
    }) => {
      const { go_getter_id, ...body } = args;
      const { data } = await client.patch(`/admin/go_getters/${go_getter_id}`, body);
      return data;
    },

    remove_go_getter: async (args: { go_getter_id: number }) => {
      const { data } = await client.delete(`/admin/go_getters/${args.go_getter_id}`);
      return data;
    },

    list_go_getters: async () => {
      const { data } = await client.get("/admin/go_getters");
      return data;
    },

    add_best_pal: async (args: {
      name: string;
      telegram_chat_id: number;
      is_admin?: boolean;
    }) => {
      const { data } = await client.post("/admin/best_pals", args);
      return data;
    },

    update_best_pal: async (args: {
      best_pal_id: number;
      name?: string;
      telegram_chat_id?: number;
      is_admin?: boolean;
    }) => {
      const { best_pal_id, ...body } = args;
      const { data } = await client.patch(`/admin/best_pals/${best_pal_id}`, body);
      return data;
    },

    remove_best_pal: async (args: { best_pal_id: number }) => {
      const { data } = await client.delete(`/admin/best_pals/${args.best_pal_id}`);
      return data;
    },

    list_best_pals: async () => {
      const { data } = await client.get("/admin/best_pals");
      return data;
    },
  };
}
