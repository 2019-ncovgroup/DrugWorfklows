from simtk.openmm.app import *
from simtk.openmm import *
from simtk.unit import *
import sys

def get_restraints(restraints_file):
    force_constants = []
    with open(restraints_file, 'r') as pdb:
        for line in pdb:
            if not isinstance(line, str):
                line = line.decode('utf-8')
            typ = line[:6]
            if typ == "ATOM  " or typ == "HETATM":
                force_constants.append(line[54:60]) # using occupancy; for temperature factor use [60:66]
    return force_constants

def make_restraint_force(pos, restraints_file='../../../constraint/cons.pdb'):
#    force = CustomExternalForce("scale*k*unit*((x-x0)^2+(y-y0)^2+(z-z0)^2)")
    force = CustomExternalForce("scale*k*unit*((periodicdistance(x, y, z, x0, y0, z0))^2)")
    force.addGlobalParameter("unit", 1.0*kilocalories_per_mole/angstrom**2) 
    force.addGlobalParameter("scale", 1.0) # to control the strength of restraint
    force.addPerParticleParameter("k")
    force.addPerParticleParameter("x0")
    force.addPerParticleParameter("y0")
    force.addPerParticleParameter("z0")
    
    force_constants = get_restraints(restraints_file)
    if len(pos) != len(force_constants):
        sys.exit("Mismatch in restraint file and system!")
    for i, atom_crd in enumerate(pos):
        #Add per particle params k x0 y0 z0
        #this should fix the particle to x0 y0 z0
        parms = [float(force_constants[i]), atom_crd.x*angstroms, atom_crd.y*angstroms, atom_crd.z*angstroms]
        force.addParticle(i, parms) # assuming that positions are in Angstroms 
    return force

inpcrd = AmberInpcrdFile('../../../build/complex.crd')
prmtop = AmberPrmtopFile('../../../build/complex.prmtop')

system = prmtop.createSystem(nonbondedMethod=PME, nonbondedCutoff=1.2*nanometer, constraints=HBonds)
res_force = make_restraint_force(inpcrd.positions)
system.addForce(res_force)

platform = Platform.getPlatformByName('CUDA')
properties = {'Precision': 'mixed'}
#properties = {'Precision': 'mixed', 'DisablePmeStream': '\'true\''}
integrator = LangevinIntegrator(50*kelvin, 5/picosecond, 0.002*picoseconds)
simulation = Simulation(prmtop.topology, system, integrator, platform, properties)
simulation.context.setPositions(inpcrd.positions)
if inpcrd.boxVectors is not None:
    simulation.context.setPeriodicBoxVectors(*inpcrd.boxVectors)

# Minimization
scale = 10.0
for i in range(10):
    simulation.context.setParameter("scale", scale)
    simulation.minimizeEnergy(maxIterations=100)
    scale = scale*0.5

simulation.context.setParameter("scale", 0.0)
simulation.minimizeEnergy(maxIterations=1000)
simulation.saveState('eq0.xml')

# Heating from 50 to 300 K
simulation.context.setParameter("scale", 1.0)
temperature = 50
#integrator.setStepSize(0.001*picoseconds)
simulation.reporters.append(StateDataReporter('eq1.log', 2500, step=True, potentialEnergy=True, temperature=True))
for i in range(250):
    simulation.step(10)
    temperature += 1
    integrator.setTemperature(temperature*kelvin)
simulation.step(2500)
simulation.saveState('eq1.xml')

