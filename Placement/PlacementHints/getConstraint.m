%%Copyright © BBP/EPFL 2005-2011; All rights reserved. Do not distribute without further notice
function maxHeight= getConstraint ( neuron, neuronName, maxHeightDendrite,binsNB,Layer,layerNB)
%returns the pia

indices= find (layerNB==5);
MPInd = getMorphIndices(indices, neuron, neuronName);
maxHeight= max(maxHeightDendrite(MPInd))+Layer(5).From+(Layer(5).To-Layer(5).From)/binsNB;

