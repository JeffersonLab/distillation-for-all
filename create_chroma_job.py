#!env python

import argparser
import functools
import operator
import kaon


def output_chroma_shell_job(chroma_args, geom, output_files, nodes, maxtime, job_name, output, facility_name, filename):
    """
    Output a script
    """

    # Get schema
    facilities_schema = kaon.get_schema_from_json("facilities.json")
    kaon.check_schema(facilities_schema)
    facility = kaon.execute_schema(facilities_schema, {'facility': [faciltity_name]})
    if len(facility) == 0:
        raise Exception(
            'The facility `{}` does not appear in `facilities.json`'.format(facility_name))
    facility = facility[0]
    sbatch_extra = facility['sbatch_extra']
    chroma_env = facility['chroma_env']
    procs = functool.reduce(operator.mul, [int(x) for x in geom.split()], 1)
    num_cores = int(facility['num_cores'])
    cores_per_process = num_cores * int(nodes) // procs
    output_files = " ".join(output_files)
    chroma_args = " ".join(chroma_args)

    with open(filename, 'wt') as fd:
        fd.write(f"""
#!/bin/bash
#SBATCH -t {maxtime} --nodes={nodes} -n {procs} -J {job_name}
#SBATCH {sbatch_extra}
#KAON_BATCH -t {maxtime} --nodes={nodes} -n {procs} {sbatch_extra}

run() {
source {chroma_env}
export MKL_NUM_THREADS={cores_per_process}
export OMP_NUM_THREADS={cores_per_process}

rm -f {output_files}
echo RUNNING chroma > {output}
{chroma_srun} -n {procs} $MY_OFFSET {chroma_bin} {chroma_args} {chroma_extra_args} -geom {geom} >> {output} && echo FINISHED chroma >> {output}
}
check() {
    grep -q "FINISHED chroma" {output} && exit 0
    exit 1
}
if [ $2 == run ]; then
    run
elif [ $2 == check ]; then
    check
elif [ $2 == out ]; then
    ls {output_files} 2>/dev/null || true
else
    exit 1
fi
""")


def process_args():
    """
    Parser commandline arguments and do the thing
    """

    parser = argprarse.ArgumentParser(description="Create a slurm job")
    parser.add_argument("--output-files", required=False, nargs='+',
                        help="Files to be removed before the execution", default=[])
    parser.add_argument("--chroma-arguments", required=True, nargs='+',
                        help="Launch a chroma job with these arguments", default=[])
    parser.add_argument("--geom", required=True, nargs=4,
                        help="Number of processes in each lattice direction")
    parser.add_argument("--facility", required=True, nargs=1, help="This facility name")
    parser.add_argument("--job-output", required=True, nargs=1,
                        help="Full path of the job's output")
    parser.add_argument("--nodes", required=True, nargs=1, type=int,
                        help="Number of nodes running chroma")
    parser.add_argument("--maxtime", required=True, nargs=1, help="Maximum time of the job")
    parser.add_argument("--job-name", nargs=1, required=False, help="Job name", default="chroma")
    parser.add_argument("--output-shell-file", nargs=1, required=True,
                        help="filename of the created the shell script")
    args = parser.parse_args()
    output_chroma_shell_jobs(chroma_args=args.chroma_arguments, geom=args.geom, remove_files=args.output_files, nodes=args.nodes,
                             maxtime=args.maxtime, job_name=args.job_name, output=args.job_output, facility_name=args.facitlity, filename=args.output_shell_file)


if __name__ == "__main__":
    process_args()
