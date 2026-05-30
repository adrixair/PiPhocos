let gLangEn = 1;
let gLangFr = 2;

let gCurLang = gLangFr;

let translations = [
    // HTML element ID  English (1)  French (2)

    // Navigation bar
    ["navbar_dropdown_language", "Language", "Langue"],

    // Side bar
    ["sidebar_headline_overview", "Overview", "Vue d'ensemble"],
    ["sidebar_dashboard", "Dashboard", "Tableau de bord"],
    ["sidebar_today", "Today", "Aujourd'hui"],
    ["sidebar_statistics", "Statistics", "Statistiques"],
    ["sidebar_headline_history", "History", "Historique"],
    ["sidebar_by_day", "By Day", "Par jour"],
    ["sidebar_by_month", "By Month", "Par mois"],
    ["sidebar_by_year", "By Year", "Par année"],
    ["sidebar_all_time", "All Time", "Total"],
    ["sidebar_headline_misc", "Misc", "Divers"],
    ["sidebar_csv", "CSV Download", "Téléchargement CSV"],
    ["sidebar_live_telemetry", "Phocos", "Phocos"],

    // Headings
    ["headline_dashboard", "Dashboard", "Tableau de bord"],
    ["headline_statistics", "Statistics", "Statistiques"],
    ["headline_csv", "CSV Download", "Téléchargement CSV"],

    // Statistics
    ["stats_card_highest_prod", "Highest Production", "Production maximale"],
    ["stats_card_best_day", "Best Day", "Meilleur jour"],
    ["stats_card_best_month", "Best Month", "Meilleur mois"],
    ["stats_card_best_year", "Best Year", "Meilleure année"],
    ["stats_card_averages", "Averages", "Moyennes"],
    ["stats_card_runtime", "Runtime", "Fonctionnement"],
    ["statistics_text_avg_daily_prod", "Average daily production", "Production quotidienne moyenne"],
    ["statistics_text_start_date", "Date of commissioning", "Date de mise en service"],
    ["statistics_text_runtime", "Total runtime", "Durée totale de fonctionnement"],

    // Dashboard
    ["dashboard_subtitle", "Last updated: ", "Dernière mise à jour : "],
    ["dash_card_current", "Grid & Home", "Réseau et maison"],
    ["dash_card_battery", "Battery", "Batterie"],
    ["dash_card_today", "Solar & Charging", "Solaire et charge"],
    ["dash_card_all_time", "Device & Status", "Appareil et état"],
    ["dash_card_24h", "Latest Data", "Dernières données"],
    ["dash_card_live_flow", "Live flow", "Flux en direct"],
    ["dash_flow_node_solar", "Solar", "Solaire"],
    ["dash_flow_node_grid", "Grid", "Réseau"],
    ["dash_flow_node_hub", "Inverter", "Onduleur"],
    ["dash_flow_node_home", "Home", "Maison"],
    ["dash_flow_node_battery", "Battery", "Batterie"],

    // History
    ["history_card_earned", "Earnings", "Gains"],
    ["history_card_usage", "Usage of Produced Energy", "Usage de l'énergie produite"],
    ["history_card_consumption", "Power Consumption", "Consommation électrique"],
    ["history_text_produced", "Energy produced", "Énergie produite"],
    ["history_text_earned_feedin", "Earned with feed-in", "Gain grâce à l'injection"],
    ["history_text_earned_self", "Saved via self-consumption", "Économie grâce à l'autoconsommation"],
    ["history_text_earned_total", "Total", "Total"],
    ["history_text_fedin", "Sent to grid", "Vers le réseau"],
    ["history_text_self_consumed", "Used by house", "Utilisée par la maison"],
    ["history_text_battery_charge", "To battery (est.)", "Vers la batterie (est.)"],
    ["history_text_consumption_grid", "From grid", "Depuis le réseau"],
    ["history_text_consumption_self", "From solar (est.)", "Depuis le solaire (est.)"],
    ["history_text_consumption_battery", "From battery", "Depuis la batterie"],
    ["history_text_consumption_total", "Total consumption", "Consommation totale"],
    ["history_card_graph_production_text", "Production Details", "Détails de la production"],
    ["history_card_graph_consumption_text", "Consumption Details", "Détails de la consommation"],
    ["history_card_autarky", "Autonomy", "Autonomie"],
    ["history_text_autarky", "Achieved autonomy", "Autonomie atteinte"],
    ["history_card_high_res_data_text", "Course of the Day", "Courbe du jour"],

    // CSV download
    ["csv_subtitle", "Download .csv reports", "Télécharger les rapports .csv"],
    ["csv_label_time_range", "Time range:", "Période :"],
    ["csv_label_resolution", "Resolution:", "Granularité :"],
    ["csv_range_rad_lbl_day", "One day", "Un jour"],
    ["csv_range_rad_lbl_month", "One month", "Un mois"],
    ["csv_range_rad_lbl_year", "One year", "Une année"],
    ["csv_range_rad_lbl_all", "All time", "Total"],
    ["csv_res_rad_lbl_day", "Single days", "Jours individuels"],
    ["csv_res_rad_lbl_month", "Summed by month", "Agrégé par mois"],
    ["csv_res_rad_lbl_year", "Summed by year", "Agrégé par année"],
    ["csv_button_download", "Download", "Télécharger"],

    // Months combo box
    ["cbx_month_1", "January", "Janvier"],
    ["cbx_month_2", "February", "Février"],
    ["cbx_month_3", "March", "Mars"],
    ["cbx_month_4", "April", "Avril"],
    ["cbx_month_5", "May", "Mai"],
    ["cbx_month_6", "June", "Juin"],
    ["cbx_month_7", "July", "Juillet"],
    ["cbx_month_8", "August", "Août"],
    ["cbx_month_9", "September", "Septembre"],
    ["cbx_month_10", "October", "Octobre"],
    ["cbx_month_11", "November", "Novembre"],
    ["cbx_month_12", "December", "Décembre"],

    // CSV months combo box
    ["csv_cbx_month_1", "January", "Janvier"],
    ["csv_cbx_month_2", "February", "Février"],
    ["csv_cbx_month_3", "March", "Mars"],
    ["csv_cbx_month_4", "April", "Avril"],
    ["csv_cbx_month_5", "May", "Mai"],
    ["csv_cbx_month_6", "June", "Juin"],
    ["csv_cbx_month_7", "July", "Juillet"],
    ["csv_cbx_month_8", "August", "Août"],
    ["csv_cbx_month_9", "September", "Septembre"],
    ["csv_cbx_month_10", "October", "Octobre"],
    ["csv_cbx_month_11", "November", "Novembre"],
    ["csv_cbx_month_12", "December", "Décembre"],

    // Info
    ["info_no_data", "No data is available for the selected time span.", "Aucune donnée n'est disponible pour la période sélectionnée."],
];

let chartStrings = [
    // Chart string ID         English (1)       French (2)
    ["chart_produced_w", "Solar production", "Production solaire"],
    ["chart_consumed_w", "Home consumption", "Consommation maison"],
    ["chart_fed_in_w", "To grid", "Vers le réseau"],
    ["chart_from_grid", "Grid consumption", "Consommation réseau"],
    ["chart_from_pv", "From solar", "Depuis le solaire"],
    ["chart_from_battery", "Battery consumption", "Consommation batterie"],
    ["chart_produced", "Production", "Production"],
    ["chart_consumed", "Consumption", "Consommation"],
    ["chart_fed_in", "To grid", "Vers le réseau"],
    ["chart_used_by_house", "Used by house", "Utilisée par la maison"],
    ["chart_to_battery", "To battery", "Vers la batterie"],
    ["chart_produced_self_kwh", "Used by house", "Utilisée par la maison"],
    ["chart_produced_battery_kwh", "To battery", "Vers la batterie"],
    ["chart_produced_grid_kwh", "To grid", "Vers le réseau"],
    ["chart_consumed_pv_kwh", "From solar", "Depuis le solaire"],
    ["chart_consumed_battery_kwh", "From battery", "Depuis la batterie"],
    ["chart_consumed_grid_kwh", "From grid", "Depuis le réseau"],
    ["chart_total", "Total", "Total"],
];

let historyStrings = [
    // History string ID   English (1)      French (2)
    ["daily_data", "Daily Data", "Données journalières"],
    ["monthly_data", "Monthly Data", "Données mensuelles"],
    ["yearly_data", "Yearly Data", "Données annuelles"],
    ["all_time_data", "All Time Data", "Données totales"],
];

let dashboardMetricStrings = [
    ["metric_ac_input_voltage", "Supply voltage", "Tension secteur"],
    ["metric_ac_input_frequency", "Supply frequency", "Fréquence secteur"],
    ["metric_ac_output_voltage", "Output voltage", "Tension en sortie"],
    ["metric_ac_output_frequency", "Output frequency", "Fréquence en sortie"],
    ["metric_ac_output_active_power", "Power in use", "Puissance utilisée"],
    ["metric_ac_output_apparent_power", "Apparent power", "Puissance apparente"],
    ["metric_ac_output_load", "Inverter load", "Charge de l'onduleur"],
    ["metric_battery_soc", "State of charge", "État de charge"],
    ["metric_battery_state", "Battery status", "État de la batterie"],
    ["metric_battery_voltage", "Battery voltage", "Tension batterie"],
    ["metric_battery_voltage_scc", "Battery voltage (solar charger)", "Tension batterie (solaire)"],
    ["metric_battery_charge_current", "Charge current", "Courant de charge"],
    ["metric_battery_discharge_current", "Discharge current", "Courant de décharge"],
    ["metric_total_charging_current", "Total charging current", "Courant total de charge"],
    ["metric_battery_priority", "Battery charge priority", "Priorité de charge batterie"],
    ["metric_pv_voltage", "Solar voltage", "Tension solaire"],
    ["metric_pv_current", "Solar current", "Courant solaire"],
    ["metric_pv_power", "Solar production", "Production solaire"],
    ["metric_pv_charging_power", "Solar charging power", "Puissance de charge solaire"],
    ["metric_mppt_active", "Solar tracking active", "Suivi solaire actif"],
    ["metric_solar_charging", "Solar charging active", "Charge solaire active"],
    ["metric_ac_charging", "Grid charging active", "Charge secteur active"],
    ["metric_bus_voltage", "Internal voltage", "Tension interne"],
    ["metric_inverter_temperature", "Inverter temperature", "Température onduleur"],
    ["metric_serial_number", "Serial number", "Numéro de série"],
    ["metric_protocol_id", "Protocol", "Protocole"],
    ["metric_operation_mode", "Current mode", "Mode actuel"],
    ["metric_ac_output_mode", "Installation role", "Rôle de l'installation"],
    ["metric_output_priority", "Power source priority", "Source prioritaire"],
    ["metric_other_units", "Other inverters detected", "Autres onduleurs détectés"],
    ["metric_fault", "Current fault", "Défaut actuel"],
    ["metric_ac_input_available", "Grid available", "Secteur disponible"],
    ["metric_ac_output_on", "Loads powered", "Maison alimentée"],
    ["metric_active_warnings", "Active warnings", "Alertes actives"],
];

let historyInfoStrings = {
    produced_kwh: [
        "Total solar energy produced over the selected period.",
        "Énergie solaire totale produite sur la période sélectionnée.",
    ],
    produced_to_house_kwh: [
        "Estimated share of solar production used immediately in the home instead of charging the battery or being sent to the grid.",
        "Part estimée de la production solaire utilisée immédiatement dans la maison, au lieu de charger la batterie ou de partir vers le réseau.",
    ],
    produced_to_battery_kwh: [
        "Estimated share of solar production sent to battery charging over the selected period.",
        "Part estimée de la production solaire envoyée vers la charge batterie sur la période sélectionnée.",
    ],
    usage_fed_in_kwh: [
        "Energy exported to the grid over the selected period.",
        "Énergie injectée sur le réseau pendant la période sélectionnée.",
    ],
    consumed_from_grid_kwh: [
        "Estimated share of total consumption supplied by the grid or another external source.",
        "Part estimée de la consommation totale fournie par le réseau ou une autre source externe.",
    ],
    consumed_from_pv_kwh: [
        "Estimated share of total consumption supplied directly by solar production.",
        "Part estimée de la consommation totale alimentée directement par la production solaire.",
    ],
    consumed_from_battery_kwh: [
        "Estimated share of total consumption supplied by battery discharge.",
        "Part estimée de la consommation totale alimentée par la décharge batterie.",
    ],
    consumed_total_kwh: [
        "Total energy used by the home or connected appliances over the selected period.",
        "Énergie totale utilisée par la maison ou les appareils raccordés sur la période sélectionnée.",
    ],
    earned_feedin: [
        "Estimated feed-in revenue using the export tariff configured in the app.",
        "Revenu d'injection estimé à partir du tarif d'export configuré dans l'application.",
    ],
    earned_savings: [
        "Estimated savings from using your own solar energy instead of buying the same energy from the grid.",
        "Économies estimées grâce à l'utilisation de votre propre énergie solaire au lieu de l'acheter au réseau.",
    ],
    earned_total: [
        "Estimated total benefit: feed-in revenue plus self-consumption savings.",
        "Bénéfice total estimé : revenu d'injection plus économies d'autoconsommation.",
    ],
    autarky: [
        "Share of total consumption covered locally by solar and battery, without buying energy from the grid.",
        "Part de la consommation totale couverte localement par le solaire et la batterie, sans achat d'énergie au réseau.",
    ],
};

let dashboardInfoStrings = {
    no_direct_values: [
        "No direct Phocos value is available in this section.",
        "Aucune valeur directe Phocos n'est disponible dans cette section.",
    ],
    tooltip_current_prefix: [
        "Current value: ",
        "Valeur actuelle : ",
    ],
};

let dashboardFieldHelpStrings = {
    metric_ac_input_voltage: [
        "Voltage currently present on the external supply input, whether it comes from the grid or a generator. If it is outside the accepted range, the inverter will not use that source.",
        "Tension actuellement présente sur l'alimentation externe, qu'elle vienne du réseau ou d'un générateur. Si elle sort de la plage acceptée, l'onduleur n'utilisera pas cette source.",
    ],
    metric_ac_input_frequency: [
        "Frequency currently detected on the external supply input. If it leaves the accepted window, the inverter treats that source as invalid.",
        "Fréquence actuellement détectée sur l'alimentation externe. Si elle sort de la fenêtre acceptée, l'onduleur considère cette source comme invalide.",
    ],
    metric_ac_output_voltage: [
        "Voltage actually delivered by the inverter to the home or connected appliances.",
        "Tension réellement délivrée par l'onduleur à la maison ou aux appareils raccordés.",
    ],
    metric_ac_output_frequency: [
        "Frequency actually delivered by the inverter to the home or connected appliances.",
        "Fréquence réellement délivrée par l'onduleur à la maison ou aux appareils raccordés.",
    ],
    metric_ac_output_active_power: [
        "Real power currently used by the home or connected appliances. This is the most useful value to follow actual consumption.",
        "Puissance réellement utilisée en ce moment par la maison ou les appareils raccordés. C'est la valeur la plus utile pour suivre la consommation réelle.",
    ],
    metric_ac_output_apparent_power: [
        "Total apparent power in volt-amperes. It can be higher than the real power when the appliances are not purely resistive.",
        "Puissance apparente totale en volt-ampères. Elle peut être supérieure à la puissance réelle lorsque les appareils ne sont pas purement résistifs.",
    ],
    metric_ac_output_load: [
        "Current load as a percentage of the inverter's rated continuous output. Close to 100% means the unit is near its nominal limit.",
        "Charge actuelle en pourcentage de la puissance continue nominale de l'onduleur. Proche de 100 %, l'appareil approche sa limite nominale.",
    ],
    metric_battery_soc: [
        "Approximate battery state of charge reported by the inverter or battery communication interface. Useful for operation, but less precise than a dedicated battery monitor.",
        "État de charge approximatif remonté par l'onduleur ou l'interface de communication batterie. Utile en exploitation, mais moins précis qu'un moniteur batterie dédié.",
    ],
    metric_operation_mode: [
        "Current operating state of the inverter. In Stand-By the output is off; in Grid mode the external supply can power the home and charge the battery; in Off-grid mode the home is supplied by solar and/or battery; Fault mode means protective shutdown logic is active.",
        "État de fonctionnement actuel de l'onduleur. En veille, l'alimentation est coupée ; en mode réseau, l'alimentation externe peut alimenter la maison et charger la batterie ; en mode autonome, la maison est alimentée par le solaire et/ou la batterie ; le mode défaut indique une logique de protection active.",
    ],
    metric_battery_state: [
        "Battery status reported by the inverter: normal, low, disconnected, or temporarily blocked by the battery management system.",
        "État batterie remonté par l'onduleur : normal, faible, déconnectée, ou temporairement bloquée par le système de gestion batterie.",
    ],
    metric_battery_voltage: [
        "Current battery voltage seen by the inverter. It helps confirm whether the battery is charging, resting, or being discharged.",
        "Tension batterie actuellement vue par l'onduleur. Elle aide à confirmer si la batterie charge, est au repos ou se décharge.",
    ],
    metric_battery_voltage_scc: [
        "Battery voltage seen by the solar charger stage. Useful to compare charger behavior with the main battery voltage.",
        "Tension batterie vue par l'étage de charge solaire. Utile pour comparer le comportement du chargeur avec la tension batterie principale.",
    ],
    metric_battery_charge_current: [
        "Current flowing into the battery while it is charging.",
        "Courant entrant dans la batterie pendant la charge.",
    ],
    metric_battery_discharge_current: [
        "Current delivered by the battery while it is supplying energy.",
        "Courant fourni par la batterie lorsqu'elle alimente le système.",
    ],
    metric_total_charging_current: [
        "Combined charging current currently going into the battery from all active charging sources.",
        "Courant total de charge entrant actuellement dans la batterie depuis toutes les sources de charge actives.",
    ],
    metric_output_priority: [
        "Chooses which source powers the home first. On Any-Grid, common priorities are external supply first, solar first, or solar then battery then supply.",
        "Choisit quelle source alimente la maison en priorité. Sur Any-Grid, les priorités courantes sont secteur d'abord, solaire d'abord, ou solaire puis batterie puis secteur.",
    ],
    metric_battery_priority: [
        "Chooses how the battery is charged. On Any-Grid, solar can be prioritized, used together with the external supply, or used alone; in Off-grid mode, charging is solar only.",
        "Choisit comment la batterie est chargée. Sur Any-Grid, le solaire peut être prioritaire, utilisé avec le secteur, ou utilisé seul ; en mode autonome, la charge se fait uniquement par le solaire.",
    ],
    metric_pv_voltage: [
        "Voltage currently available from the solar panels at the MPPT input.",
        "Tension actuellement disponible depuis les panneaux solaires à l'entrée MPPT.",
    ],
    metric_pv_current: [
        "Current currently provided by the solar panels at the MPPT input.",
        "Courant actuellement fourni par les panneaux solaires à l'entrée MPPT.",
    ],
    metric_pv_power: [
        "Instant solar power currently available from the panels.",
        "Puissance solaire instantanée actuellement disponible depuis les panneaux.",
    ],
    metric_pv_charging_power: [
        "Solar power currently being used to charge the battery.",
        "Puissance solaire actuellement utilisée pour charger la batterie.",
    ],
    metric_mppt_active: [
        "Shows whether the solar tracker is actively harvesting energy from the panels.",
        "Indique si le régulateur solaire récupère activement de l'énergie depuis les panneaux.",
    ],
    metric_solar_charging: [
        "Shows whether solar charging is currently active.",
        "Indique si la charge solaire est actuellement active.",
    ],
    metric_ac_charging: [
        "Shows whether the battery is currently charging from the external supply.",
        "Indique si la batterie est actuellement en charge depuis le secteur.",
    ],
    metric_bus_voltage: [
        "Internal DC voltage inside the inverter. This is mainly a diagnostic value rather than a day-to-day operating figure.",
        "Tension continue interne de l'onduleur. C'est surtout une valeur de diagnostic plutôt qu'un indicateur d'usage quotidien.",
    ],
    metric_inverter_temperature: [
        "Internal inverter temperature. If it rises too much, the unit can reduce power or enter protection.",
        "Température interne de l'onduleur. Si elle monte trop, l'appareil peut réduire sa puissance ou passer en protection.",
    ],
    metric_serial_number: [
        "Factory serial number of the inverter. Useful for support, warranty and product identification.",
        "Numéro de série usine de l'onduleur. Utile pour le support, la garantie et l'identification du produit.",
    ],
    metric_protocol_id: [
        "Communication family reported by the inverter firmware, such as PI30. This is mainly useful for compatibility and support.",
        "Famille de communication remontée par le firmware de l'onduleur, par exemple PI30. Cette information sert surtout à la compatibilité et au support.",
    ],
    metric_ac_output_mode: [
        "Installation role of this unit: standalone inverter, parallel unit, or one phase in a multi-unit system.",
        "Rôle de cette unité dans l'installation : onduleur seul, unité en parallèle, ou phase d'un système multi-unités.",
    ],
    metric_other_units: [
        "Shows whether this inverter detects other Any-Grid units on the same installation.",
        "Indique si cet onduleur détecte d'autres unités Any-Grid sur la même installation.",
    ],
    metric_fault: [
        "Current fault requiring attention. Faults can include over-temperature, battery voltage problems, overload, output short-circuit, solar over-voltage or communication faults.",
        "Défaut actuel nécessitant une attention. Les défauts peuvent inclure surchauffe, problème de tension batterie, surcharge, court-circuit en sortie, surtension solaire ou défaut de communication.",
    ],
    metric_ac_input_available: [
        "Shows whether the external supply is present and accepted by the inverter.",
        "Indique si le secteur est présent et accepté par l'onduleur.",
    ],
    metric_ac_output_on: [
        "Shows whether the inverter is actively powering the home or connected appliances.",
        "Indique si l'onduleur alimente actuellement la maison ou les appareils raccordés.",
    ],
    metric_active_warnings: [
        "Warnings currently raised by the inverter, such as fan lock, over-temperature, low battery, overload, lost battery communication or lithium battery protection.",
        "Alertes actuellement remontées par l'onduleur, par exemple ventilateur bloqué, surchauffe, batterie faible, surcharge, perte de communication batterie ou protection batterie lithium.",
    ],
};

let dashboardValueStrings = {
    metric_battery_state: {
        "Battery voltage normal": ["Battery normal", "Batterie normale"],
        "Battery voltage low": ["Battery low", "Batterie faible"],
        "Battery disconnected": ["Battery disconnected", "Batterie déconnectée"],
        "Battery charging/discharging disabled by BMS": ["Blocked by battery protection", "Bloquée par la protection batterie"],
        "Unknown": ["Unknown", "Inconnu"],
    },
    metric_battery_priority: {
        "Utility first": ["Grid first", "Secteur prioritaire"],
        "Solar first": ["Solar first", "Solaire prioritaire"],
        "Solar and Utility": ["Solar + grid", "Solaire + secteur"],
        "Solar only": ["Solar only", "Solaire uniquement"],
        "Unknown": ["Unknown", "Inconnu"],
    },
    metric_operation_mode: {
        "Powered on": ["Starting", "Démarrage"],
        "Stand-By": ["Standby", "Veille"],
        "Grid / Line mode": ["Grid mode", "Mode réseau"],
        "Off-grid / Battery mode": ["Off-grid mode", "Mode autonome"],
        "Fault mode": ["Fault mode", "Mode défaut"],
        "Shutdown mode": ["Off", "Arrêt"],
        "Unknown": ["Unknown", "Inconnu"],
    },
    metric_ac_output_mode: {
        "Single Any-Grid unit": ["Single inverter", "Onduleur seul"],
        "Parallel output": ["Parallel system", "Système en parallèle"],
        "Phase 1 of 3-phase output": ["3-phase system - phase 1", "Triphasé - phase 1"],
        "Phase 2 of 3-phase output": ["3-phase system - phase 2", "Triphasé - phase 2"],
        "Phase 3 of 3-phase output": ["3-phase system - phase 3", "Triphasé - phase 3"],
        "Unknown": ["Unknown", "Inconnu"],
    },
    metric_output_priority: {
        "Utility first": ["Grid first", "Secteur prioritaire"],
        "Solar first": ["Solar first", "Solaire prioritaire"],
        "SBU": ["Solar, battery, then grid", "Solaire, batterie puis secteur"],
        "Battery first": ["Battery first", "Batterie prioritaire"],
        "Unknown": ["Unknown", "Inconnu"],
    },
    metric_fault: {
        "No fault": ["None", "Aucun"],
        "Unknown": ["Unknown", "Inconnu"],
    },
};

let genericStrings = {
    unavailable: ["Unavailable", "Indisponible"],
    loading_statistics: ["Loading statistics...", "Chargement des statistiques..."],
    loading_history: ["Loading selected period...", "Chargement de la période sélectionnée..."],
    statistics_load_error: ["Could not load statistics.", "Impossible de charger les statistiques."],
    history_load_error: ["Could not load this period.", "Impossible de charger cette période."],
    boolean_yes: ["Yes", "Oui"],
    boolean_no: ["No", "Non"],
    none: ["None", "Aucune"],
    unit_days: ["days", "jours"],
    stats_best_year_prefix: ["in ", "en "],
    dashboard_stale_note: [
        "Offline: no recent measurement, live values are forced to zero.",
        "Hors live : aucune mesure récente, les valeurs directes sont forcées à zéro.",
    ],
    dashboard_partial_note: [
        "Today's totals exclude one or more communication outages or gaps.",
        "Les totaux du jour excluent une ou plusieurs coupures ou pertes de communication.",
    ],
    flow_state_idle: ["Standby", "Veille"],
    flow_state_solar_active: ["Solar active", "Production active"],
    flow_state_import: ["Importing", "Import"],
    flow_state_export: ["Exporting", "Injection"],
    flow_state_available: ["Available", "Disponible"],
    flow_state_home_active: ["Live load", "Charge en cours"],
    flow_state_charging: ["Charging", "Charge"],
    flow_state_discharging: ["Discharging", "Décharge"],
    flow_state_live: ["Live", "Temps réel"],
    flow_state_delayed: ["Offline", "Hors live"],
    telemetry_status_connected: ["Phocos connected", "Phocos connecté"],
    telemetry_status_disconnected: ["Phocos disconnected", "Phocos déconnecté"],
    telemetry_detail_last_sample: ["Last sample ", "Dernière mesure "],
    telemetry_detail_waiting: ["Last sample unavailable", "Dernière mesure indisponible"],
    history_incomplete_note: [
        "This period is incomplete: one or more outages or communication gaps were excluded from the totals.",
        "Cette période est incomplète : une ou plusieurs coupures ou pertes de communication ont été exclues des totaux.",
    ],
};


function restoreLanguage() {
    var lang = localStorage.getItem("lang");
    if (lang != null)
        switchLanguageByIndex(parseInt(lang));
    else
        switchLanguageByIndex(gLangEn);
}

function switchLanguageToEnglish() {
    switchLanguageByIndex(gLangEn);
}

function switchLanguageToFrench() {
    switchLanguageByIndex(gLangFr);
}

function syncLanguageMenuState() {
    [
        { id: "navbar_dropdown_language_en", index: gLangEn },
        { id: "navbar_dropdown_language_fr", index: gLangFr },
    ].forEach(entry => {
        const option = document.getElementById(entry.id);
        if (option == null)
            return;

        const selected = entry.index === gCurLang;
        option.classList.toggle("active", selected);
        option.setAttribute("aria-current", selected ? "true" : "false");
    });
}

function switchLanguageByIndex(index) {
    if (index != gLangEn && index != gLangFr)
        index = gLangFr;

    gCurLang = index;
    localStorage.setItem("lang", index);
    document.documentElement.lang = getHtmlLanguageTag();

    translations.forEach(translation => {
        try {
            document.getElementById(translation[0]).innerHTML = translation[index];
        } catch (error) {
            console.error("Could not localize element " + translation[0] + ": " + error);
        }
    });

    syncLanguageMenuState();

    if (typeof refreshLocalizedContent === "function" && typeof gAppInitialized !== "undefined" && gAppInitialized)
        refreshLocalizedContent();
}

function getChartString(id) {
    for (i = 0; i < chartStrings.length; ++i)
        if (chartStrings[i][0] == id)
            return chartStrings[i][gCurLang];
    return "...";
}

function getHistoryString(id) {
    for (i = 0; i < historyStrings.length; ++i)
        if (historyStrings[i][0] == id)
            return historyStrings[i][gCurLang];
    return "...";
}

function getTextString(id) {
    for (i = 0; i < translations.length; ++i)
        if (translations[i][0] == id)
            return translations[i][gCurLang];
    return "...";
}

function getDashboardMetricString(id) {
    for (i = 0; i < dashboardMetricStrings.length; ++i)
        if (dashboardMetricStrings[i][0] == id)
            return dashboardMetricStrings[i][gCurLang];
    return "...";
}

function getDashboardInfoString(id) {
    if (dashboardInfoStrings[id] != undefined)
        return dashboardInfoStrings[id][gCurLang - 1];
    return "...";
}

function getDashboardFieldHelpString(id) {
    if (dashboardFieldHelpStrings[id] != undefined)
        return dashboardFieldHelpStrings[id][gCurLang - 1];
    return "";
}

function getHistoryInfoString(id) {
    if (historyInfoStrings[id] != undefined)
        return historyInfoStrings[id][gCurLang - 1];
    return "...";
}

function localizeDashboardValue(id, value) {
    const labelMap = dashboardValueStrings[id];
    if (labelMap == null || value == null)
        return value;
    const localizedValue = labelMap[String(value)];
    if (localizedValue == null)
        return value;
    return localizedValue[gCurLang - 1];
}

function getGenericString(id) {
    if (genericStrings[id] != undefined)
        return genericStrings[id][gCurLang - 1];
    return "...";
}


const gNumberFormatters = new Map();

function getNumberFormatter(locale, digits) {
    const safeDigits = Math.max(0, Math.min(6, Number.isFinite(Number(digits)) ? Number(digits) : 0));
    const cacheKey = locale + ":" + safeDigits;
    if (!gNumberFormatters.has(cacheKey)) {
        gNumberFormatters.set(cacheKey, new Intl.NumberFormat(locale, {
            minimumFractionDigits: safeDigits,
            maximumFractionDigits: safeDigits,
        }));
    }
    return gNumberFormatters.get(cacheKey);
}

function numFormat(number, digits) {
    if (number === null || number === undefined || Number.isNaN(Number(number)) || !Number.isFinite(Number(number)))
        return getGenericString("unavailable");
    const locale = gCurLang == gLangFr ? "fr-FR" : "en-US";
    return getNumberFormatter(locale, digits).format(number);
}


let monthNames = [
    // English (1), French (2)
    ["January", "Janvier"],
    ["February", "Février"],
    ["March", "Mars"],
    ["April", "Avril"],
    ["May", "Mai"],
    ["June", "Juin"],
    ["July", "Juillet"],
    ["August", "Août"],
    ["September", "Septembre"],
    ["October", "Octobre"],
    ["November", "Novembre"],
    ["December", "Décembre"],
];

function getMonthName(index) {
    return monthNames[index][gCurLang - 1];
}

function getLocale() {
    return gCurLang == gLangFr ? "fr-FR" : "en-US";
}

function getHtmlLanguageTag() {
    return gCurLang == gLangFr ? "fr" : "en";
}

function getUnitDays() {
    return getGenericString("unit_days");
}

function getStatsBestYearPrefix() {
    return getGenericString("stats_best_year_prefix");
}

function prettyPrintDateString(date) {
    var d = new Date(date);
    let localeDate = d.toLocaleString(getLocale(), {
        weekday: "long",
        day: "numeric",
        year: "numeric",
        month: "long",
        timeZone: "Europe/Paris",
    });
    return localeDate;
}

function prettyPrintDateStringWithoutDay(date) {
    var d = new Date(date);
    let localeDate = d.toLocaleString(getLocale(), {
        year: "numeric",
        month: "long",
        timeZone: "Europe/Paris",
    });
    return localeDate;
}
