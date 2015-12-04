function txt = myupdatefcn(empt,event_obj,MPIndices,neuronName,dcm_obj)
%allows displaying name of neuron after clicking on point of graph

DI = get(event_obj,'DataIndex');
info_struct = getCursorInfo(dcm_obj);
txt = ['Name: ', neuronName(MPIndices(DI))];
