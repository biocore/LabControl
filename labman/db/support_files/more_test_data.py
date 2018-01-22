from datetime import datetime
from itertools import chain

import numpy as np

from labman.db.process import (
    SamplePlatingProcess, GDNAExtractionProcess, GDNAPlateCompressionProcess,
    LibraryPrep16SProcess, NormalizationProcess, QuantificationProcess,
    LibraryPrepShotgunProcess, PoolingProcess)
from labman.db.user import User
from labman.db.plate import PlateConfiguration, Plate
from labman.db.equipment import Equipment
from labman.db.composition import ReagentComposition

# Sample Plating
user = User('test@foo.bar')
plate_config = PlateConfiguration(1)
sp_process = SamplePlatingProcess.create(
    user, plate_config, 'Test plate %s' % datetime.now())
sp_process.update_well(1, 1, '1.SKB8.640193')
sp_process.update_well(1, 2, '1.SKD8.640184')
sp_process.update_well(1, 3, '1.SKB7.640196')
sp_process.update_well(1, 4, '1.SKM9.640192')
sp_process.update_well(1, 5, '1.SKM4.640180')
sp_process.update_well(1, 6, '1.SKM5.640177')
sp_process.update_well(1, 7, '1.SKB5.640181')
sp_process.update_well(1, 8, '1.SKD6.640190')
sp_process.update_well(1, 9, '1.SKB2.640194')

sample_plate = sp_process.plate

# gDNA extraction
ep_robot = Equipment(6)
kf_robot = Equipment(11)
tool = Equipment(15)
kit = ReagentComposition(1)
plates_info = [(sample_plate, kf_robot, ep_robot, tool, kit,
                'gdna test plate %s' % datetime.now())]
ext_process = GDNAExtractionProcess.create(user, plates_info, 75)
gdna_plate = ext_process.plates[0]

# Amplicon library prep
master_mix = ReagentComposition(2)
water = ReagentComposition(3)
tm300_8_tool = Equipment(16)
tm50_8_tool = Equipment(17)
plates_info = [(gdna_plate, 'New 16S plate %s' % datetime.now(), Plate(11),
                ep_robot, tm300_8_tool, tm50_8_tool, master_mix, water)]
amplicon_process = LibraryPrep16SProcess.create(user, plates_info, 10)
amplicon_plate = amplicon_process.plates[0]

# gDNA compression
comp_process = GDNAPlateCompressionProcess.create(
    user, [gdna_plate], 'Compressed plate %s' % datetime.now())
compressed_plate = comp_process.plates[0]

# gDNA compressed quantification
concentrations = np.around(np.random.rand(16, 24), 6)
quant_process = QuantificationProcess.create(user, compressed_plate,
                                             concentrations)

# Normalization process
norm_process = NormalizationProcess.create(
    user, quant_process, water, 'Norm plate %s' % datetime.now())
norm_plate = norm_process.plates[0]

# Library prep shotgun
kappa = ReagentComposition(4)
stub = ReagentComposition(5)
shotgun_process = LibraryPrepShotgunProcess.create(
    user, norm_plate, 'Test Shotgun Library %s' % datetime.now(), kappa, stub,
    4000, Plate(19), Plate(20))
shotgun_plate = shotgun_process.plates[0]

quant_process2 = QuantificationProcess.create(user, compressed_plate,
                                              concentrations)

input_compositions = []
echo = Equipment(8)
for well in chain.from_iterable(shotgun_plate.layout):
    if well is not None:
        input_compositions.append({
            'composition': well.composition, 'input_volume': 1,
            'percentage_of_output': 1/9.0})
pool_process = PoolingProcess.create(
    user, quant_process2, 'New test pool name %s' % datetime.now(), 4,
    input_compositions, echo)
