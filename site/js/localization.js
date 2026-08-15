let gLangFr = 1;

let gCurLang = gLangFr;

let translations = [
    // ID element HTML  Français (1)

    // Barre laterale
    ["sidebar_headline_overview", "Vue d'ensemble"],
    ["sidebar_dashboard", "Tableau de bord"],
    ["sidebar_today", "Aujourd'hui"],
    ["sidebar_statistics", "Statistiques"],
    ["sidebar_headline_history", "Historique"],
    ["sidebar_by_day", "Par jour"],
    ["sidebar_by_month", "Par mois"],
    ["sidebar_by_year", "Par année"],
    ["sidebar_all_time", "Total"],
    ["sidebar_headline_misc", "Divers"],
    ["sidebar_csv", "Téléchargement CSV"],
    ["sidebar_live_telemetry", ""],

    // Titres
    ["headline_dashboard", "Tableau de bord"],
    ["headline_statistics", "Statistiques"],
    ["headline_csv", "Téléchargement CSV"],

    // Statistiques
    ["stats_card_highest_prod", "Production maximale"],
    ["stats_card_best_day", "Meilleur jour"],
    ["stats_card_best_month", "Meilleur mois"],
    ["stats_card_best_year", "Meilleure année"],
    ["stats_card_averages", "Moyennes"],
    ["stats_card_runtime", "Fonctionnement"],
    ["statistics_text_avg_daily_prod", "Production quotidienne moyenne"],
    ["statistics_text_start_date", "Date de mise en service"],
    ["statistics_text_runtime", "Durée totale de fonctionnement"],

    // Tableau de bord
    ["dashboard_subtitle", "Dernière mise à jour : "],
    ["dash_card_current", "Réseau et maison"],
    ["dash_card_battery", "Batterie"],
    ["dash_card_today", "Solaire et charge"],
    ["dash_card_all_time", "Appareil et état"],
    ["dash_card_phocos_settings", "Paramètres Phocos"],
    ["dash_card_24h", "Dernières données"],
    ["dash_card_live_flow", "Flux en direct"],
    ["dash_flow_node_solar", "Solaire"],
    ["dash_flow_node_grid", "Réseau"],
    ["dash_flow_node_hub", "Onduleur"],
    ["dash_flow_node_home", "Maison"],
    ["dash_flow_node_battery", "Batterie"],
    // Historique
    ["history_card_earned", "Facture et économies"],
    ["history_card_usage", "Usage de l'énergie produite"],
    ["history_card_consumption", "Consommation électrique"],
    ["history_text_produced", "Énergie produite"],
    ["history_text_earned_feedin", "Crédit injection"],
    ["history_text_earned_self", "Économie solaire"],
    ["history_text_bill_total", "Coût brut"],
    ["history_text_earned_total", "Facture estimée"],
    ["history_text_fedin", "Vers le réseau"],
    ["history_text_self_consumed", "Utilisée par la maison"],
    ["history_text_battery_charge", "Vers la batterie (est.)"],
    ["history_text_consumption_grid", "Depuis le réseau"],
    ["history_text_consumption_self", "Depuis le solaire (est.)"],
    ["history_text_consumption_battery", "Depuis la batterie"],
    ["history_text_consumption_total", "Consommation totale"],
    ["history_card_graph_production_text", "Détails de la production"],
    ["history_card_graph_consumption_text", "Détails de la consommation"],
    ["history_card_autarky", "Autonomie"],
    ["history_text_autarky", "Autonomie atteinte"],
    ["history_card_high_res_data_text", "Courbe du jour"],

    // Telechargement CSV
    ["csv_subtitle", "Télécharger les rapports .csv"],
    ["csv_label_time_range", "Période :"],
    ["csv_label_resolution", "Granularité :"],
    ["csv_range_rad_lbl_day", "Un jour"],
    ["csv_range_rad_lbl_month", "Un mois"],
    ["csv_range_rad_lbl_year", "Une année"],
    ["csv_range_rad_lbl_all", "Total"],
    ["csv_res_rad_lbl_day", "Jours individuels"],
    ["csv_res_rad_lbl_month", "Agrégé par mois"],
    ["csv_res_rad_lbl_year", "Agrégé par année"],
    ["csv_button_download", "Télécharger"],

    // Liste des mois
    ["cbx_month_1", "Janvier"],
    ["cbx_month_2", "Février"],
    ["cbx_month_3", "Mars"],
    ["cbx_month_4", "Avril"],
    ["cbx_month_5", "Mai"],
    ["cbx_month_6", "Juin"],
    ["cbx_month_7", "Juillet"],
    ["cbx_month_8", "Août"],
    ["cbx_month_9", "Septembre"],
    ["cbx_month_10", "Octobre"],
    ["cbx_month_11", "Novembre"],
    ["cbx_month_12", "Décembre"],

    // Liste des mois CSV
    ["csv_cbx_month_1", "Janvier"],
    ["csv_cbx_month_2", "Février"],
    ["csv_cbx_month_3", "Mars"],
    ["csv_cbx_month_4", "Avril"],
    ["csv_cbx_month_5", "Mai"],
    ["csv_cbx_month_6", "Juin"],
    ["csv_cbx_month_7", "Juillet"],
    ["csv_cbx_month_8", "Août"],
    ["csv_cbx_month_9", "Septembre"],
    ["csv_cbx_month_10", "Octobre"],
    ["csv_cbx_month_11", "Novembre"],
    ["csv_cbx_month_12", "Décembre"],

    // Information
    ["info_no_data", "Aucune donnée n'est disponible pour la période sélectionnée."],
];

let chartStrings = [
    // ID libelle graphique  Français (1)
    ["chart_produced_w", "Production solaire"],
    ["chart_consumed_w", "Consommation maison"],
    ["chart_fed_in_w", "Vers le réseau"],
    ["chart_from_grid", "Consommation réseau"],
    ["chart_from_pv", "Depuis le solaire"],
    ["chart_from_battery", "Consommation batterie"],
    ["chart_produced", "Production"],
    ["chart_consumed", "Consommation"],
    ["chart_fed_in", "Vers le réseau"],
    ["chart_used_by_house", "Utilisée par la maison"],
    ["chart_to_battery", "Vers la batterie"],
    ["chart_produced_self_kwh", "Utilisée par la maison"],
    ["chart_produced_battery_kwh", "Vers la batterie"],
    ["chart_produced_grid_kwh", "Vers le réseau"],
    ["chart_consumed_pv_kwh", "Depuis le solaire"],
    ["chart_consumed_battery_kwh", "Depuis la batterie"],
    ["chart_consumed_grid_kwh", "Depuis le réseau"],
    ["chart_total", "Total"],
];

let historyStrings = [
    // ID historique  Français (1)
    ["daily_data", "Données journalières"],
    ["monthly_data", "Données mensuelles"],
    ["yearly_data", "Données annuelles"],
    ["all_time_data", "Données totales"],
];

let dashboardMetricStrings = [
    ["metric_ac_input_voltage", "Tension secteur"],
    ["metric_ac_input_frequency", "Fréquence secteur"],
    ["metric_ac_output_voltage", "Tension en sortie"],
    ["metric_ac_output_frequency", "Fréquence en sortie"],
    ["metric_ac_output_active_power", "Puissance utilisée"],
    ["metric_ac_output_apparent_power", "Puissance apparente"],
    ["metric_ac_output_load", "Charge de l'onduleur"],
    ["metric_total_output_active_power", "Sortie active totale"],
    ["metric_total_output_apparent_power", "Sortie apparente totale"],
    ["metric_solar_to_house", "Solaire vers maison"],
    ["metric_battery_to_house", "Batterie vers maison"],
    ["metric_grid_to_house", "Réseau vers maison"],
    ["metric_battery_soc", "État de charge"],
    ["metric_battery_state", "État de la batterie"],
    ["metric_battery_type", "Type batterie"],
    ["metric_battery_voltage", "Tension batterie"],
    ["metric_battery_voltage_scc", "Tension batterie (solaire)"],
    ["metric_battery_charge_current", "Courant de charge"],
    ["metric_battery_discharge_current", "Courant de décharge"],
    ["metric_battery_charge_power", "Puissance de charge"],
    ["metric_battery_discharge_power", "Puissance de décharge"],
    ["metric_total_charging_current", "Courant total de charge"],
    ["metric_battery_rating_voltage", "Tension nominale batterie"],
    ["metric_battery_bulk_voltage", "Tension bulk"],
    ["metric_battery_float_voltage", "Tension float"],
    ["metric_battery_recharge_voltage", "Tension de recharge"],
    ["metric_battery_redischarge_voltage", "Tension de redécharge"],
    ["metric_battery_under_voltage", "Seuil sous-tension"],
    ["metric_max_charging_current", "Courant charge max"],
    ["metric_max_ac_charging_current", "Courant charge secteur max"],
    ["metric_battery_priority", "Priorité de charge batterie"],
    ["metric_pv_voltage", "Tension solaire"],
    ["metric_pv_current", "Courant solaire"],
    ["metric_pv_power", "Production solaire"],
    ["metric_pv_charging_power", "Puissance de charge solaire"],
    ["metric_solar_to_battery", "Solaire vers batterie"],
    ["metric_solar_feed_to_grid", "Solaire vers réseau"],
    ["metric_grid_to_battery", "Réseau vers batterie"],
    ["metric_mppt_active", "Suivi solaire actif"],
    ["metric_solar_charging", "Charge solaire active"],
    ["metric_ac_charging", "Charge secteur active"],
    ["metric_pv_ok_condition", "Condition d'acceptation PV"],
    ["metric_pv_power_balance", "Équilibrage puissance PV"],
    ["metric_bus_voltage", "Tension interne"],
    ["metric_inverter_temperature", "Température onduleur"],
    ["metric_serial_number", "Numéro de série"],
    ["metric_protocol_id", "Protocole"],
    ["metric_device_id", "ID appareil"],
    ["metric_operation_mode", "Mode actuel"],
    ["metric_ac_output_mode", "Rôle de l'installation"],
    ["metric_output_priority", "Source prioritaire"],
    ["metric_other_units", "Autres onduleurs détectés"],
    ["metric_input_voltage_range", "Plage tension entrée"],
    ["metric_machine_type", "Type machine"],
    ["metric_topology", "Topologie"],
    ["metric_rated_active_power", "Puissance active nominale"],
    ["metric_rated_apparent_power", "Puissance apparente nominale"],
    ["metric_rated_output_current", "Courant sortie nominal"],
    ["metric_battery_redischarge_voltage_scc", "Tension de redécharge solaire"],
    ["metric_cv_charge_time", "Durée charge CV"],
    ["metric_battery_type_code", "Code type batterie"],
    ["metric_charger_priority_code", "Code priorité chargeur"],
    ["metric_grid_rating_voltage", "Tension nominale réseau"],
    ["metric_grid_rating_current", "Courant nominal réseau"],
    ["metric_output_rating_voltage", "Tension nominale sortie"],
    ["metric_output_rating_frequency", "Fréquence nominale sortie"],
    ["metric_max_parallel_units", "Unités parallèles max"],
    ["metric_country_code", "Code pays"],
    ["metric_input_voltage_range_code", "Code plage entrée"],
    ["metric_output_priority_code", "Code priorité sortie"],
    ["metric_machine_type_code", "Code type machine"],
    ["metric_topology_code", "Code topologie"],
    ["metric_pv_ok_condition_code", "Code condition PV"],
    ["metric_pv_power_balance_code", "Code équilibre PV"],
    ["metric_reserved_setting_26", "Réglage réservé 26"],
    ["metric_reserved_setting_27", "Réglage réservé 27"],
    ["metric_fault", "Défaut actuel"],
    ["metric_ac_input_available", "Secteur disponible"],
    ["metric_ac_output_on", "Maison alimentée"],
    ["metric_active_warnings", "Alertes actives"],
    ["metric_warning_bitmap", "Bits d'alerte"],
    ["metric_flag_blob", "Flags actifs"],
    ["metric_status_bits", "Bits d'état"],
];

let historyInfoStrings = {
    produced_kwh: [
        "Énergie solaire totale produite sur la période sélectionnée.",
    ],
    produced_to_house_kwh: [
        "Part estimée de la production solaire utilisée immédiatement dans la maison, au lieu de charger la batterie ou de partir vers le réseau.",
    ],
    produced_to_battery_kwh: [
        "Part estimée de la production solaire envoyée vers la charge batterie sur la période sélectionnée.",
    ],
    usage_fed_in_kwh: [
        "Énergie injectée sur le réseau pendant la période sélectionnée.",
    ],
    consumed_from_grid_kwh: [
        "Part estimée de la consommation totale fournie par le réseau ou une autre source externe.",
    ],
    consumed_from_pv_kwh: [
        "Part estimée de la consommation totale alimentée directement par la production solaire.",
    ],
    consumed_from_battery_kwh: [
        "Part estimée de la consommation totale alimentée par la décharge batterie.",
    ],
    consumed_total_kwh: [
        "Énergie totale utilisée par la maison ou les appareils raccordés sur la période sélectionnée.",
    ],
    earned_feedin: [
        "Crédit estimé pour l'énergie injectée sur le réseau, soustrait de la facture quand il existe.",
    ],
    earned_savings: [
        "Économie TTC estimée grâce à l'énergie solaire utilisée sur place au lieu d'acheter ces kWh au réseau. Ce n'est pas une remise EDF.",
    ],
    earned_total: [
        "Montant TTC estimé de la facture à payer sur la période. L'abonnement fixe TTC est inclus au prix réel configuré, même si la consommation est faible.",
    ],
    bill_without_self_consumption_eur: [
        "Coût brut TTC de l'électricité consommée au tarif réseau classique, abonnement fixe TTC proratisé inclus.",
    ],
    autarky: [
        "Part de la consommation totale couverte localement par le solaire et la batterie, sans achat d'énergie au réseau.",
    ],
};

let dashboardInfoStrings = {
    no_direct_values: [
        "Aucune valeur directe Phocos n'est disponible dans cette section.",
    ],
    tooltip_current_prefix: [
        "Valeur actuelle : ",
    ],
};

let dashboardFieldHelpStrings = {
    metric_ac_input_voltage: [
        "Tension actuellement présente sur l'alimentation externe, qu'elle vienne du réseau ou d'un générateur. Si elle sort de la plage acceptée, l'onduleur n'utilisera pas cette source.",
    ],
    metric_ac_input_frequency: [
        "Fréquence actuellement détectée sur l'alimentation externe. Si elle sort de la fenêtre acceptée, l'onduleur considère cette source comme invalide.",
    ],
    metric_ac_output_voltage: [
        "Tension réellement délivrée par l'onduleur à la maison ou aux appareils raccordés.",
    ],
    metric_ac_output_frequency: [
        "Fréquence réellement délivrée par l'onduleur à la maison ou aux appareils raccordés.",
    ],
    metric_ac_output_active_power: [
        "Puissance réellement utilisée en ce moment par la maison ou les appareils raccordés. C'est la valeur la plus utile pour suivre la consommation réelle.",
    ],
    metric_ac_output_apparent_power: [
        "Puissance apparente totale en volt-ampères. Elle peut être supérieure à la puissance réelle lorsque les appareils ne sont pas purement résistifs.",
    ],
    metric_ac_output_load: [
        "Charge actuelle en pourcentage de la puissance continue nominale de l'onduleur. Proche de 100 %, l'appareil approche sa limite nominale.",
    ],
    metric_battery_soc: [
        "État de charge approximatif remonté par l'onduleur ou l'interface de communication batterie. Utile en exploitation, mais moins précis qu'un moniteur batterie dédié.",
    ],
    metric_operation_mode: [
        "État de fonctionnement actuel de l'onduleur. En veille, l'alimentation est coupée ; en mode réseau, l'alimentation externe peut alimenter la maison et charger la batterie ; en mode autonome, la maison est alimentée par le solaire et/ou la batterie ; le mode défaut indique une logique de protection active.",
    ],
    metric_battery_state: [
        "État batterie remonté par l'onduleur : normal, faible, déconnectée, ou temporairement bloquée par le système de gestion batterie.",
    ],
    metric_battery_voltage: [
        "Tension batterie actuellement vue par l'onduleur. Elle aide à confirmer si la batterie charge, est au repos ou se décharge.",
    ],
    metric_battery_voltage_scc: [
        "Tension batterie vue par l'étage de charge solaire. Utile pour comparer le comportement du chargeur avec la tension batterie principale.",
    ],
    metric_battery_charge_current: [
        "Courant entrant dans la batterie pendant la charge.",
    ],
    metric_battery_discharge_current: [
        "Courant fourni par la batterie lorsqu'elle alimente le système.",
    ],
    metric_total_charging_current: [
        "Courant total de charge entrant actuellement dans la batterie depuis toutes les sources de charge actives.",
    ],
    metric_output_priority: [
        "Choisit quelle source alimente la maison en priorité. Sur Any-Grid, les priorités courantes sont secteur d'abord, solaire d'abord, ou solaire puis batterie puis secteur.",
    ],
    metric_battery_priority: [
        "Choisit comment la batterie est chargée. Sur Any-Grid, le solaire peut être prioritaire, utilisé avec le secteur, ou utilisé seul ; en mode autonome, la charge se fait uniquement par le solaire.",
    ],
    metric_pv_voltage: [
        "Tension actuellement disponible depuis les panneaux solaires à l'entrée MPPT.",
    ],
    metric_pv_current: [
        "Courant actuellement fourni par les panneaux solaires à l'entrée MPPT.",
    ],
    metric_pv_power: [
        "Puissance solaire instantanée actuellement disponible depuis les panneaux.",
    ],
    metric_pv_charging_power: [
        "Puissance solaire actuellement utilisée pour charger la batterie.",
    ],
    metric_mppt_active: [
        "Indique si le régulateur solaire récupère activement de l'énergie depuis les panneaux.",
    ],
    metric_solar_charging: [
        "Indique si la charge solaire est actuellement active.",
    ],
    metric_ac_charging: [
        "Indique si la batterie est actuellement en charge depuis le secteur.",
    ],
    metric_bus_voltage: [
        "Tension continue interne de l'onduleur. C'est surtout une valeur de diagnostic plutôt qu'un indicateur d'usage quotidien.",
    ],
    metric_inverter_temperature: [
        "Température interne de l'onduleur. Si elle monte trop, l'appareil peut réduire sa puissance ou passer en protection.",
    ],
    metric_serial_number: [
        "Numéro de série usine de l'onduleur. Utile pour le support, la garantie et l'identification du produit.",
    ],
    metric_protocol_id: [
        "Famille de communication remontée par le firmware de l'onduleur, par exemple PI30. Cette information sert surtout à la compatibilité et au support.",
    ],
    metric_ac_output_mode: [
        "Rôle de cette unité dans l'installation : onduleur seul, unité en parallèle, ou phase d'un système multi-unités.",
    ],
    metric_other_units: [
        "Indique si cet onduleur détecte d'autres unités Any-Grid sur la même installation.",
    ],
    metric_fault: [
        "Défaut actuel nécessitant une attention. Les défauts peuvent inclure surchauffe, problème de tension batterie, surcharge, court-circuit en sortie, surtension solaire ou défaut de communication.",
    ],
    metric_ac_input_available: [
        "Indique si le secteur est présent et accepté par l'onduleur.",
    ],
    metric_ac_output_on: [
        "Indique si l'onduleur alimente actuellement la maison ou les appareils raccordés.",
    ],
    metric_active_warnings: [
        "Alertes actuellement remontées par l'onduleur, par exemple ventilateur bloqué, surchauffe, batterie faible, surcharge, perte de communication batterie ou protection batterie lithium.",
    ],
};

let dashboardValueStrings = {
    metric_battery_state: {
        "Battery voltage normal": ["Batterie normale"],
        "Battery voltage low": ["Batterie faible"],
        "Battery disconnected": ["Batterie déconnectée"],
        "Battery charging/discharging disabled by BMS": ["Bloquée par la protection batterie"],
        "Unknown": ["Inconnu"],
    },
    metric_battery_type: {
        "AGM": ["AGM"],
        "Flooded": ["Plomb ouvert"],
        "User defined": ["Personnalisée"],
        "Lithium": ["Lithium"],
        "Unknown": ["Inconnu"],
    },
    metric_battery_priority: {
        "Utility first": ["Secteur prioritaire"],
        "Solar first": ["Solaire prioritaire"],
        "Solar and Utility": ["Solaire + secteur"],
        "Solar only": ["Solaire uniquement"],
        "Unknown": ["Inconnu"],
    },
    metric_operation_mode: {
        "Powered on": ["Démarrage"],
        "Stand-By": ["Veille"],
        "Grid / Line mode": ["Mode réseau"],
        "Off-grid / Battery mode": ["Mode autonome"],
        "Fault mode": ["Mode défaut"],
        "Shutdown mode": ["Arrêt"],
        "Unknown": ["Inconnu"],
    },
    metric_other_units: {
        "Single unit only": ["Onduleur unique"],
        "Multiple units connected": ["Plusieurs onduleurs connectés"],
    },
    metric_ac_output_mode: {
        "Single Any-Grid unit": ["Onduleur seul"],
        "Parallel output": ["Système en parallèle"],
        "Phase 1 of 3-phase output": ["Triphasé - phase 1"],
        "Phase 2 of 3-phase output": ["Triphasé - phase 2"],
        "Phase 3 of 3-phase output": ["Triphasé - phase 3"],
        "Unknown": ["Inconnu"],
    },
    metric_output_priority: {
        "Utility first": ["Secteur prioritaire"],
        "Solar first": ["Solaire prioritaire"],
        "SBU": ["Solaire, batterie puis secteur"],
        "Battery first": ["Batterie prioritaire"],
        "Unknown": ["Inconnu"],
    },
    metric_input_voltage_range: {
        "Appliance": ["Appareil"],
        "UPS": ["Onduleur UPS"],
        "Unknown": ["Inconnu"],
    },
    metric_machine_type: {
        "Grid tie": ["Raccordé réseau"],
        "Off-grid": ["Autonome"],
        "Hybrid": ["Hybride"],
        "Unknown hybrid variant": ["Hybride inconnu"],
        "Unknown": ["Inconnu"],
    },
    metric_topology: {
        "Transformerless": ["Sans transformateur"],
        "Transformer": ["Avec transformateur"],
        "Unknown": ["Inconnu"],
    },
    metric_pv_ok_condition: {
        "PV power at any level": ["Puissance PV à tout niveau"],
        "PV power must exceed configured threshold": ["PV au-dessus du seuil configuré"],
        "Unknown": ["Inconnu"],
    },
    metric_pv_power_balance: {
        "PV power balance disabled": ["Désactivé"],
        "PV power balance enabled": ["Activé"],
        "Unknown": ["Inconnu"],
    },
    metric_fault: {
        "No fault": ["Aucun"],
        "Unknown": ["Inconnu"],
    },
};

let genericStrings = {
    unavailable: ["Indisponible"],
    loading_statistics: ["Chargement des statistiques..."],
    loading_history: ["Chargement de la période sélectionnée..."],
    statistics_load_error: ["Impossible de charger les statistiques."],
    history_load_error: ["Impossible de charger cette période."],
    boolean_yes: ["Oui"],
    boolean_no: ["Non"],
    none: ["Aucune"],
    unit_days: ["jours"],
    stats_best_year_prefix: ["en "],
    dashboard_stale_note: [
        "Hors live : aucune mesure récente, les valeurs directes sont forcées à zéro.",
    ],
    dashboard_partial_note: [
        "Les totaux du jour excluent une ou plusieurs coupures ou pertes de communication.",
    ],
    flow_state_idle: ["Veille"],
    flow_state_solar_active: ["Production active"],
    flow_state_import: ["Import"],
    flow_state_export: ["Injection"],
    flow_state_available: ["Disponible"],
    flow_state_home_active: ["Charge en cours"],
    flow_state_charging: ["Charge"],
    flow_state_discharging: ["Décharge"],
    flow_state_live: ["Temps réel"],
    flow_state_delayed: ["Hors live"],
    telemetry_status_connected: ["Phocos connecté"],
    telemetry_status_disconnected: ["Phocos déconnecté"],
    telemetry_detail_last_sample: ["Dernière mesure "],
    telemetry_detail_waiting: ["Dernière mesure indisponible"],
    history_incomplete_note: [
        "Cette période est incomplète : une ou plusieurs coupures ou pertes de communication ont été exclues des totaux.",
    ],
};


function restoreLanguage() {
    switchLanguageByIndex(gLangFr);
}

function syncLanguageMenuState() {
}

function switchLanguageByIndex(index) {
    if (index != gLangFr)
        index = gLangFr;

    gCurLang = index;
    localStorage.setItem("lang", index);
    document.documentElement.lang = getHtmlLanguageTag();

    translations.forEach(translation => {
        try {
            document.getElementById(translation[0]).innerHTML = translation[gLangFr];
        } catch (error) {
            console.error("Localisation impossible pour " + translation[0] + " : " + error);
        }
    });

    syncLanguageMenuState();

    if (typeof refreshLocalizedContent === "function" && typeof gAppInitialized !== "undefined" && gAppInitialized)
        refreshLocalizedContent();
}

function getChartString(id) {
    for (i = 0; i < chartStrings.length; ++i)
        if (chartStrings[i][0] == id)
            return chartStrings[i][gLangFr];
    return "...";
}

function getHistoryString(id) {
    for (i = 0; i < historyStrings.length; ++i)
        if (historyStrings[i][0] == id)
            return historyStrings[i][gLangFr];
    return "...";
}

function getTextString(id) {
    for (i = 0; i < translations.length; ++i)
        if (translations[i][0] == id)
            return translations[i][gLangFr];
    return "...";
}

function getDashboardMetricString(id) {
    for (i = 0; i < dashboardMetricStrings.length; ++i)
        if (dashboardMetricStrings[i][0] == id)
            return dashboardMetricStrings[i][gLangFr];
    return "...";
}

function getDashboardInfoString(id) {
    if (dashboardInfoStrings[id] != undefined)
        return dashboardInfoStrings[id][0];
    return "...";
}

function getDashboardFieldHelpString(id) {
    if (dashboardFieldHelpStrings[id] != undefined)
        return dashboardFieldHelpStrings[id][0];
    return "";
}

function getHistoryInfoString(id) {
    if (historyInfoStrings[id] != undefined)
        return historyInfoStrings[id][0];
    return "...";
}

function localizeDashboardValue(id, value) {
    const labelMap = dashboardValueStrings[id];
    if (labelMap == null || value == null)
        return value;
    const localizedValue = labelMap[String(value)];
    if (localizedValue == null)
        return value;
    return localizedValue[0];
}

function getGenericString(id) {
    if (genericStrings[id] != undefined)
        return genericStrings[id][0];
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
    return getNumberFormatter("fr-FR", digits).format(number);
}


let monthNames = [
    // Français (1)
    ["Janvier"],
    ["Février"],
    ["Mars"],
    ["Avril"],
    ["Mai"],
    ["Juin"],
    ["Juillet"],
    ["Août"],
    ["Septembre"],
    ["Octobre"],
    ["Novembre"],
    ["Décembre"],
];

function getMonthName(index) {
    return monthNames[index][0];
}

function getLocale() {
    return "fr-FR";
}

function getHtmlLanguageTag() {
    return "fr";
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
