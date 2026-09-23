import os, sys
from pepper_lab.datastructuresoil import *
from pepper_lab.modeling import *
from pepper_lab.predict import *
pep = Pepper(pepper_data_location=os.path.expanduser('~/build'))
pep.set_tag('all_data'); pep.set_setup_name('uncertainty_paper_soil'); pep.set_data_type('soil')
pep.set_target_variable_name('logDT50_mean'); pep.set_target_variable_std_name('logDT50_std')
pep.set_smiles_name('SMILES'); pep.set_compound_name('compound_name')
soil = DataStructureSoil(pep)
soil.curate_annotate(from_csv=True, from_paper=True)
soil.reduce_for_modelling(from_csv=False)
d = Descriptors(pep); d.set_data(soil)
d.load_descriptors(from_csv=False, enviPath_prob=False, enviPath_trig=False, mordred=False,
                   PaDEL=True, MACCS=False, RDKit_descriptors=False, avalonfps=False, RDKit_fps=False)
m = Modeling(pep, soil, d)
model = m.build_final_model(regressor_name='GPR', feature_space='padel', config='soil_paper_GPR_optimized')
print("DONE", model.regressor)
