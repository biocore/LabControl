#!/usr/bin/env python

from datetime import datetime
from itertools import chain

import numpy as np
import click

from labman.db.process import (
    SamplePlatingProcess, GDNAExtractionProcess, GDNAPlateCompressionProcess,
    LibraryPrep16SProcess, NormalizationProcess, QuantificationProcess,
    LibraryPrepShotgunProcess, PoolingProcess, SequencingProcess)
from labman.db.user import User
from labman.db.plate import PlateConfiguration, Plate
from labman.db.equipment import Equipment
from labman.db.composition import ReagentComposition
from labman.db.sql_connection import TRN


def get_samples():
    with TRN:
        TRN.add("SELECT sample_id FROM qiita.study_sample")
        return TRN.execute_fetchflatten()


def create_sample_plate_process(user, samples):
    plate_config = PlateConfiguration(1)
    num_rows = plate_config.num_rows
    num_cols = plate_config.num_columns
    sp_process = SamplePlatingProcess.create(
        user, plate_config, 'Test plate %s' % datetime.now())

    # Plate the samples
    for idx, sample in enumerate(samples):
        i = int(idx / num_cols) + 1
        j = (idx % num_cols) + 1

        # Make sure that the user didn't pass more samples than wells
        if i > num_rows:
            break

        sp_process.update_well(i, j, sample)

    sample_plate = sp_process.plate
    return sp_process, sample_plate


def create_gdna_extraction_process(user, plate):
    kingfisher = Equipment(11)
    epmotion = Equipment(6)
    epmotion_tool = Equipment(15)
    extraction_kit = ReagentComposition(1)
    ext_process = GDNAExtractionProcess.create(
        user, plate, kingfisher, epmotion, epmotion_tool, extraction_kit, 100,
        'GDNA test plate %s' % datetime.now())
    gdna_plate = ext_process.plates[0]
    return ext_process, gdna_plate


def create_amplicon_prep(user, plate):
    primer_plate = Plate(11)
    epmotion = Equipment(6)
    master_mix = ReagentComposition(2)
    water_lot = ReagentComposition(3)
    epmotion_tool_tm300 = Equipment(16)
    epmotion_tool_tm50 = Equipment(17)
    amplicon_process = LibraryPrep16SProcess.create(
        user, plate, primer_plate, 'Amplicon test plate %s' % datetime.now(),
        epmotion, epmotion_tool_tm300, epmotion_tool_tm50, master_mix,
        water_lot, 75,)
    amplicon_plate = amplicon_process.plates[0]
    return amplicon_process, amplicon_plate


def create_compression_process(user, gdna_plates):
    comp_process = GDNAPlateCompressionProcess.create(
        user, gdna_plates, 'Compressed test plate %s' % datetime.now(),
        Equipment(6))
    compressed_plate = comp_process.plates[0]
    return comp_process, compressed_plate


def create_quantification_process(user, plate):
    plate_config = plate.plate_configuration
    concentrations = np.around(
        np.random.rand(plate_config.num_rows, plate_config.num_columns), 6)
    quant_process = QuantificationProcess.create(user, plate, concentrations)
    return quant_process


def create_pool_quantification_process(user, pools):
    concentrations = np.around(np.random.rand(len(pools)), 6)
    concentrations = [{'composition': p, 'concentration': c}
                      for p, c in zip(pools, concentrations)]
    return QuantificationProcess.create_manual(user, concentrations)


def create_normalization_process(user, quant_process):
    water = ReagentComposition(3)
    norm_process = NormalizationProcess.create(
        user, quant_process, water,
        'Normalized test plate %s' % datetime.now())
    norm_plate = norm_process.plates[0]
    return norm_process, norm_plate


def create_shotgun_process(user, norm_plate):
    kappa = ReagentComposition(4)
    stub = ReagentComposition(5)
    shotgun_process = LibraryPrepShotgunProcess.create(
        user, norm_plate, 'Test Shotgun Library %s' % datetime.now(), kappa,
        stub, 4000, Plate(19), Plate(20))
    shotgun_plate = shotgun_process.plates[0]
    return shotgun_process, shotgun_plate


def create_plate_pool_process(user, quant_process, plate, func_data):
    input_compositions = []
    echo = Equipment(8)
    for well in chain.from_iterable(plate.layout):
        if well is not None:
            input_compositions.append({
                'composition': well.composition, 'input_volume': 1,
                'percentage_of_output': 1/9.0})
    pool_process = PoolingProcess.create(
        user, quant_process, 'New test pool name %s' % datetime.now(),
        4, input_compositions, func_data, robot=echo)
    return pool_process


def create_pools_pool_process(user, quant_process, pools):
    input_compositions = [
        {'composition': p, 'input_volume': 1, 'percentage_of_output': 1/9.0}
        for p in pools]
    pool_process = PoolingProcess.create(
        user, quant_process, 'New pool name %s' % datetime.now(), 5,
        input_compositions, {"function": "amplicon_pool", "parameters": {}})
    return pool_process


def create_sequencing_process(user, pools):
    seq_process = SequencingProcess.create(
        user, pools, 'New sequencing run %s' % datetime.now(),
        'Run experiment %s' % datetime.now(), Equipment(18), 151, 151,
        User('admin@foo.bar'),
        contacts=[User('test@foo.bar'), User('demo@microbio.me')])
    return seq_process


def amplicon_workflow(user, samples):
    # Sample Plating
    sp_process, sample_plate = create_sample_plate_process(user, samples[:96])
    # gDNA extraction
    ext_process, gdna_plate = create_gdna_extraction_process(
        user, sample_plate)
    # Amplicon library prep
    amplicon_process, amplicon_plate = create_amplicon_prep(user, gdna_plate)
    # Library plate quantification
    amplicon_quant_process = create_quantification_process(
        user, amplicon_plate)
    # Plate pooling process
    plate_pool_process = create_plate_pool_process(
        user, amplicon_quant_process, amplicon_plate,
        {'function': 'amplicon',
         'parameters': {"dna_amount": 240, "min_val": 1, "max_val": 15,
                        "blank_volume": 2, "robot": 6, "destination": 1}})
    # Quantify pools
    pool_quant_process = create_pool_quantification_process(
        user, [plate_pool_process.pool])
    # Create sequencing pool process
    seq_pool_process = create_pools_pool_process(
        user, pool_quant_process, [plate_pool_process.pool])
    # Sequencing process
    create_sequencing_process(user, [seq_pool_process.pool])


def shotgun_workflow(user, samples):
    # Sample Plating
    sp_process, sample_plate = create_sample_plate_process(user, samples[:96])
    # gDNA extraction
    ext_process, gdna_plate = create_gdna_extraction_process(
        user, sample_plate)
    # gDNA compression
    comp_process, compressed_plate = create_compression_process(
        user, [gdna_plate])
    # gDNA compressed quantification
    gdna_comp_quant_process = create_quantification_process(
        user, compressed_plate)
    # Normalization process
    norm_process, norm_plate = create_normalization_process(
        user, gdna_comp_quant_process)
    # Library prep shotgun
    shotgun_process, shotgun_plate = create_shotgun_process(user, norm_plate)
    # Quantify library plate
    shotgun_quant_process = create_quantification_process(user, shotgun_plate)
    # Pooling process
    pool_process = create_plate_pool_process(
        user, shotgun_quant_process, shotgun_plate,
        {'function': 'equal', 'parameters': {'total_vol': 60, 'size': 500}})
    # Sequencing process
    create_sequencing_process(user, [pool_process.pool])


@click.command()
def integration_tests():
    samples = get_samples()
    user = User('test@foo.bar')
    amplicon_workflow(user, samples)
    shotgun_workflow(user, samples)


if __name__ == '__main__':
    integration_tests()
