%%Copyright © BBP/EPFL 2005-2011; All rights reserved. Do not distribute without further notice
function B= getTypes(path)
%function that returns all neuron types


%***************************************
%get info needed from neuronDB file (output file)
%load the NeuronDB.dat file
fid = fopen(path);
A = textscan(fid,'%s%d%s');

neuron = A{1,1};
layerNB = A{1,2};
type = A{1,3};

fclose(fid)
%***************************************

typesNB = length(type);

for i=1:typesNB
    B= unique (type);
end

