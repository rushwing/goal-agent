import { AxiosInstance } from "axios";

export function registerReportTools(client: AxiosInstance) {
  return {
    generate_daily_report: async (args: {
      pupil_id?: number;
      report_date?: string;
    }) => {
      const { data } = await client.post("/reports/daily", null, { params: args });
      return data;
    },

    generate_weekly_report: async (args: {
      pupil_id?: number;
      week_start?: string;
    }) => {
      const { data } = await client.post("/reports/weekly", null, { params: args });
      return data;
    },

    generate_monthly_report: async (args: {
      pupil_id?: number;
      year?: number;
      month?: number;
    }) => {
      const { data } = await client.post("/reports/monthly", null, { params: args });
      return data;
    },

    list_reports: async (args: {
      pupil_id?: number;
      report_type?: string;
      limit?: number;
    }) => {
      const { data } = await client.get("/reports", { params: args });
      return data;
    },
  };
}
