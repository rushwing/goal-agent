import { AxiosInstance } from "axios";

/**
 * Track taxonomy tools: discover categories and subcategories.
 *
 * Call list_track_categories before create_target or set_wizard_constraints
 * to get valid subcategory_id values.
 */
export function registerTracksTools(client: AxiosInstance) {
  return {
    list_track_categories: async () => {
      const { data } = await client.get("/tracks/categories");
      return data;
    },

    list_track_subcategories: async (args: { category_id?: number }) => {
      const { data } = await client.get("/tracks/subcategories", {
        params: args.category_id !== undefined
          ? { category_id: args.category_id }
          : {},
      });
      return data;
    },
  };
}
