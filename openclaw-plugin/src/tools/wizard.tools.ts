import { AxiosInstance } from "axios";

/**
 * Wizard tools for guided GoalGroup creation.
 *
 * Conversation flow:
 *   start_goal_group_wizard
 *     → set_wizard_scope
 *     → set_wizard_targets        (use target_ids from list_targets)
 *     → set_wizard_constraints    (use subcategory_ids from wizard.target_specs)
 *     → [check feasibility_passed in response]
 *     → confirm_goal_group        (if no blockers)
 *     → adjust_wizard + confirm   (if blockers)
 *     → cancel_goal_group_wizard  (abort at any stage)
 *
 * After set_wizard_targets the response includes target_specs with subcategory_id.
 * Use those subcategory_ids as keys in set_wizard_constraints / adjust_wizard.
 *
 * All endpoints require best_pal/admin role (enforced via X-Telegram-Chat-Id header
 * in the shared axios client).
 */

export function registerWizardTools(client: AxiosInstance) {
  return {
    start_goal_group_wizard: async (args: { go_getter_id: number }) => {
      const { data } = await client.post("/wizards", {
        go_getter_id: args.go_getter_id,
      });
      return data;
    },

    get_wizard_status: async (args: { wizard_id: number }) => {
      const { data } = await client.get(`/wizards/${args.wizard_id}`);
      return data;
    },

    set_wizard_scope: async (args: {
      wizard_id: number;
      title: string;
      start_date: string;
      end_date: string;
      description?: string;
    }) => {
      const { wizard_id, ...body } = args;
      const { data } = await client.post(`/wizards/${wizard_id}/scope`, body);
      return data;
    },

    /**
     * Set which targets to include. Pass target_ids from list_targets.
     * priorities: optional parallel list of 1-5 values (default 3).
     * The server normalises subcategory_id from the DB — just pass 0.
     */
    set_wizard_targets: async (args: {
      wizard_id: number;
      target_ids: number[];
      priorities?: number[];
    }) => {
      const target_specs = args.target_ids.map((id, i) => ({
        target_id: id,
        subcategory_id: 0, // server normalises from DB
        priority: args.priorities?.[i] ?? 3,
      }));
      const { data } = await client.post(`/wizards/${args.wizard_id}/targets`, {
        target_specs,
      });
      return data;
    },

    /**
     * Set per-target study constraints and trigger AI plan generation.
     * constraints: object keyed by subcategory_id (from wizard.target_specs).
     * Each value: { daily_minutes: number, preferred_days?: number[] }
     * preferred_days: 0=Mon … 6=Sun. Defaults to all days.
     * Expect 10-30 s per target while plans are generated.
     */
    set_wizard_constraints: async (args: {
      wizard_id: number;
      constraints: Record<
        string,
        { daily_minutes: number; preferred_days?: number[] }
      >;
    }) => {
      const { data } = await client.post(
        `/wizards/${args.wizard_id}/constraints`,
        { constraints: args.constraints }
      );
      return data;
    },

    /**
     * Adjust targets or constraints and re-generate plans.
     * Use after feasibility check reveals blockers.
     * Pass only what you want to change.
     * constraints keys are subcategory_ids.
     */
    adjust_wizard: async (args: {
      wizard_id: number;
      target_ids?: number[];
      priorities?: number[];
      constraints?: Record<
        string,
        { daily_minutes: number; preferred_days?: number[] }
      >;
    }) => {
      const body: Record<string, unknown> = {};
      if (args.target_ids !== undefined) {
        body.target_specs = args.target_ids.map((id, i) => ({
          target_id: id,
          subcategory_id: 0, // server normalises
          priority: args.priorities?.[i] ?? 3,
        }));
      }
      if (args.constraints !== undefined) {
        body.constraints = args.constraints;
      }
      const { data } = await client.post(
        `/wizards/${args.wizard_id}/adjust`,
        body
      );
      return data;
    },

    /** Finalise the wizard: creates GoalGroup and activates plans. */
    confirm_goal_group: async (args: { wizard_id: number }) => {
      const { data } = await client.post(
        `/wizards/${args.wizard_id}/confirm`
      );
      return data;
    },

    /** Cancel wizard and discard all draft plans. Safe at any stage. */
    cancel_goal_group_wizard: async (args: { wizard_id: number }) => {
      const { data } = await client.delete(`/wizards/${args.wizard_id}`);
      return data;
    },
  };
}
