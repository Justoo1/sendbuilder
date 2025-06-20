DOMAIN_PATTERNS = {
    # Subject-Level Domains
    'DM': {
        'name': 'Demographics',
        'patterns': [
            r'(?i)demographics',
            r'(?i)animal.{0,20}identif',
            r'(?i)animal.{0,20}housing',
            r'(?i)animal.{0,20}receipt',
            r'(?i)test.{0,20}system',
            r'(?i)species',
            r'(?i)strain',
        ]
    },
    'DS': {
        'name': 'Disposition',
        'patterns': [
            r'(?i)disposition',
            r'(?i)mortality',
            r'(?i)death',
            r'(?i)euthan',
            r'(?i)terminal',
            r'(?i)sacrifice',
        ]
    },
    
    # Study Design Domains
    'TS': {
        'name': 'Trial Summary',
        'patterns': [
            r'(?i)trial.{0,20}summary',
            r'(?i)study.{0,20}summar',
            r'(?i)objective',
            r'(?i)study.{0,20}design',
            r'(?i)study.{0,20}schedule',
        ]
    },
    'TA': {
        'name': 'Trial Arms',
        'patterns': [
            r'(?i)trial.{0,20}arms',
            r'(?i)study.{0,20}arms',
            r'(?i)treatment.{0,20}arms',
            r'(?i)experiment.{0,20}arms',
            r'(?i)group.{0,20}treatment',      # "Group Treatment"
            r'(?i)dose.{0,20}level',           # "Dose Level"
            r'(?i)group.{0,5}\d+',             # "Group 1", "Group 2"
            r'(?i)treatment.{0,20}group',      # "treatment group"
            r'(?i)number.{0,20}animals', 
        ]
    },
    'TE': {
        'name': 'Trial Elements',
        'patterns': [
            r'(?i)trial.{0,20}elements',
            r'(?i)study.{0,20}elements',
            r'(?i)experiment.{0,20}elements',
            r'(?i)study.{0,20}phases',
        ]
    },
    'TX': {
        'name': 'Trial Sets',
        'patterns': [
            r'(?i)trial.{0,20}sets',
            r'(?i)experimental.{0,20}design',
            r'(?i)group.{0,5}(\d+).{0,20}dose.{0,20}level',
            r'(?i)dose.{0,20}groups',
            r'(?i)treatment.{0,20}groups',
        ]
    },
    'PP': {
        'name': 'Planned Protocols',
        'patterns': [
            r'(?i)planned.{0,20}protocol',
            r'(?i)study.{0,20}protocol',
            r'(?i)protocol.{0,20}design',
        ]
    },
    'SE': {
        'name': 'Subject Elements',
        'patterns': [
            r'(?i)subject.{0,20}elements',
            r'(?i)animal.{0,20}elements',
            r'(?i)subject.{0,20}segments',
        ]
    },
    
    # Interventions Domains
    'EX': {
        'name': 'Exposure',
        'patterns': [
            r'(?i)exposure',
            r'(?i)dose.{0,20}admin',
            r'(?i)dosing.{0,20}formulation',
            r'(?i)test.{0,20}article.{0,20}admin',
           
        ]
    },
    'PC': {
        'name': 'Pharmacokinetic Concentrations',
        'patterns': [
            r'(?i)pharmacokinetic',
            r'(?i)PK.{0,20}concentr',
            r'(?i)PK.{0,20}parameters',
            r'(?i)plasma.{0,20}concentr',
            r'(?i)blood.{0,20}concentr',
        ]
    },
    'PP': {
        'name': 'Pharmacokinetic Parameters',
        'patterns': [
            r'(?i)PK.{0,20}parameters',
            r'(?i)pharmacokinetic.{0,20}parameters',
            r'(?i)AUC',
            r'(?i)Cmax',
            r'(?i)half.{0,5}life',
        ]
    },
    
    # Findings Domains
    'BW': {
        'name': 'Body Weights',
        'patterns': [
            r'(?i)body.{0,20}weights?',
            r'(?i)individual.{0,20}body.{0,20}weight',
            r'(?i)summary.{0,20}body.{0,20}weight',
            r'(?i)animal.{0,20}weights?',
        ]
    },
    'CL': {
        'name': 'Clinical Observations',
        'patterns': [
            r'(?i)clinical.{0,20}observa',
            r'(?i)clinical.{0,20}signs',
            r'(?i)individual.{0,20}clinical',
            r'(?i)summary.{0,20}clinical',
            r'(?i)clinical.*animals.*time',        # "Clinical Observations - Animals by Time"
            r'(?i)activity.*hypoactive',           # Common clinical signs
            r'(?i)salivation',                     # Specific observations
        ]
    },
    'DD': {
        'name': 'Death Diagnosis',
        'patterns': [
            r'(?i)death.{0,20}diagnosis',
            r'(?i)cause.{0,20}of.{0,20}death',
            r'(?i)mortality.{0,20}reason',
        ]
    },
    'FW': {
        'name': 'Food and Water Consumption',
        'patterns': [
            r'(?i)food.{0,20}consumption',
            r'(?i)water.{0,20}consumption',
            r'(?i)food.{0,20}intake',
            r'(?i)water.{0,20}intake',
            r'(?i)feed.{0,20}consumption',
            r'(?i)daily.{0,10}food.{0,10}cons',
            r'(?i)food.{0,10}cons.{0,10}per.{0,10}animal',
            r'(?i)individual.{0,10}food.{0,10}consumption'
        ]
    },
    'LB': {
        'name': 'Laboratory Test Results',
        'patterns': [
            r'(?i)laboratory.{0,20}test',
            r'(?i)lab.{0,20}results',
            r'(?i)clinical.{0,20}pathology',
            r'(?i)hematology',
            r'(?i)clinical.{0,20}chemistry',
            r'(?i)urinalysis',
            r'(?i)coagulation',
            r'(?i)serum.{0,20}chemistry',
            r'(?i)blood.{0,20}chemistry',
        ]
    },
    'MA': {
        'name': 'Macroscopic Findings',
        'patterns': [
            r'(?i)macroscopic.{0,20}findings',
            r'(?i)gross.{0,20}pathology',
            r'(?i)gross.{0,20}findings',
            r'(?i)necropsy.{0,20}findings',
            r'(?i)macroscopic.{0,20}observations',
            r'(?i)gross.{0,20}observations',
            r'(?i)no.{0,10}visible.{0,10}lesions', # Very common phrase (293 matches!)
            r'(?i)terminal.{0,20}necropsy',        # Terminal procedures
        ]
    },
    'MI': {
        'name': 'Microscopic Findings',
        'patterns': [
            r'(?i)microscopic.{0,20}findings',
            r'(?i)histopathology',
            r'(?i)histo.{0,5}pathology',
            r'(?i)microscopic.{0,20}examination',
            r'(?i)histopathological.{0,20}findings',
        ]
    },
    'OM': {
        'name': 'Organ Measurements',
        'patterns': [
            r'(?i)organ.{0,20}measurements',
            r'(?i)organ.{0,20}weights',
            r'(?i)relative.{0,20}organ.{0,20}weights',
            r'(?i)absolute.{0,20}organ.{0,20}weights',
        ]
    },
    'PA': {
        'name': 'Palpable Masses',
        'patterns': [
            r'(?i)palpable.{0,20}masses',
            r'(?i)palpable.{0,20}findings',
            r'(?i)tumor.{0,20}findings',
            r'(?i)mass.{0,20}palpation',
        ]
    },
    'PM': {
        'name': 'Physical Measurements',
        'patterns': [
            r'(?i)physical.{0,20}measurements',
            r'(?i)body.{0,20}measurements',
            r'(?i)body.{0,20}length',
            r'(?i)physical.{0,20}examination',
        ]
    },
    'EG': {
        'name': 'ECG Test Results',
        'patterns': [
            r'(?i)ECG',
            r'(?i)electrocardiogram',
            r'(?i)cardiac.{0,20}evaluation',
            r'(?i)heart.{0,20}rate',
            r'(?i)QT.{0,5}interval',
            r'(?i)ECG.{0,20}parameters',
        ]
    },
    'CV': {
        'name': 'Cardiovascular Test Results',
        'patterns': [
            r'(?i)cardiovascular',
            r'(?i)blood.{0,20}pressure',
            r'(?i)hemodynamic',
            r'(?i)cardiovascular.{0,20}parameters',
            r'(?i)hemodynamic.{0,20}parameters',
        ]
    },
    'VS': {
        'name': 'Vital Signs',
        'patterns': [
            r'(?i)vital.{0,20}signs',
            r'(?i)respiratory.{0,20}rate',
            r'(?i)body.{0,20}temperature',
            r'(?i)pulse.{0,20}rate',
            r'(?i)heart.{0,20}rate',
            r'(?i)temperature.{0,20}\d+',               # Temperature with numbers
            r'(?i)respiration.{0,20}rate',              # Specific to rate, not just "respiration"
            r'(?i)\d+.{0,10}bpm',                       # Beats per minute measurements
            r'(?i)\d+.{0,10}°C',                        # Temperature measurements  
            r'(?i)\d+.{0,10}breaths.{0,10}per.{0,10}minute',  # Respiratory rate format
            r'(?i)vital.{0,20}signs.{0,20}(table|data|measurement)',  # Context-specific
        ]
    },
    'CO': {
        'name': 'Comments',
        'patterns': [
            r'(?i)comments?',
            r'(?i)study.{0,20}comments?',
            r'(?i)general.{0,20}comments?',
            r'(?i)investigator.{0,20}comments?',
            r'(?i)additional.{0,20}comments?',
            r'(?i)notes?',
            r'(?i)observations?.{0,20}notes?',
            r'(?i)study.{0,20}notes?',
            r'(?i)remarks?',
            r'(?i)additional.{0,20}information',
            r'(?i)comment.{0,20}field',
            r'(?i)comment.{0,20}section',
            r'(?i)note.{0,20}to.{0,20}file',
            r'(?i)sponsor.{0,20}comments?',
            r'(?i)protocol.{0,20}deviations?',
            r'(?i)data.{0,20}clarifications?',
            r'(?i)explanation.{0,20}of',
            r'(?i)rationale.{0,20}for',
        ]
    },
}
