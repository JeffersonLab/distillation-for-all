#!/bin/bash

# NOTE: style with four spaces indentation and 100 columns

read -r -d '' hlp_msg << 'EOF'
Create SLURM jobs to create eigenvectors.

Usage:

  ... | kaon-create-jobs-eigs.sh

where:
- ..., the script reads a schema from the standard input.
EOF

if [ ${#*} -ge 1 ] && [ ${1} == -h -o ${1} == --help ]; then
    # Show help
    echo "${hlp_msg}"
    exit
elif [ ${#*} != 0 ]; then
    echo "Invalid number of arguments"
    echo "${hlp_msg}"
    exit 1
fi

node_type="`./kaon.py facilities.json --facility $THIS_FACILITY --show node_type`"
./kaon.py - --show eig_default_run cfg_file smear_fact smear_num default_vecs eig_default_file \
            space_size time_size eig_${node_type}_geom eig_${node_type}_num_nodes \
            eig_${node_type}_maxtime --columns-sep "|" | while IFS='|' read runpath cfg_file \
            smear_fact smear_num num_vecs eig_file ssize tsize geom nodes maxtime; do

    mkdir -p `dirname $runpath`
    
    #
    # Basis creation
    #
    
    [ -f ${runpath}.xml ] || cat << EOF > ${runpath}.xml
<?xml version="1.0"?>
<chroma>
 <Param>
  <InlineMeasurements>
    <elem>
      <Name>CREATE_COLORVECS_SUPERB</Name>
      <Frequency>1</Frequency>
      <Param>
        <num_vecs>$num_vecs</num_vecs>
        <decay_dir>3</decay_dir>
        <write_fingerprint>true</write_fingerprint>
        <LinkSmearing>
          <LinkSmearingType>STOUT_SMEAR</LinkSmearingType>
          <link_smear_fact>${smear_fact}</link_smear_fact>
          <link_smear_num>${smear_num}</link_smear_num>
          <no_smear_dir>3</no_smear_dir>
        </LinkSmearing>
      </Param>
      <NamedObject>
        <gauge_id>default_gauge_field</gauge_id>
        <colorvec_out>${eig_file}</colorvec_out>
      </NamedObject>
    </elem>
  </InlineMeasurements>
  <nrow>$ssize $ssize $ssize $tsize</nrow>
  </Param>
  <RNG>
    <Seed>
      <elem>2551</elem>
      <elem>3189</elem>
      <elem>2855</elem>
      <elem>707</elem>
    </Seed>
  </RNG>
  <Cfg>
    <cfg_type>SCIDAC</cfg_type>
    <cfg_file>${cfg_file}</cfg_file>
    <parallel_io>true</parallel_io>
  </Cfg>
</chroma>
EOF

    ./create_chroma_job.py --chroma-arguments "-i ${runpath}.xml" --geom $geom \
        --facility ${THIS_FACILITY} --job-output ${runpath}.out --nodes $nodes \
        --maxtime $maxtime --job-name ${runpath//\//-} --output-shell-file ${runpath}.sh
done
