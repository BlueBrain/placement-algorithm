function axoneAbove(MPIndices, difference, neuronName , cType, fid )
%this function prints in a file the neurons which have an axon higher than the dendrites
%the output file is as follows : neuronName, type, difference between Axon
%and Dendrite heights

for i = 1 : length (MPIndices)
    if difference (MPIndices(i)) > 0
        
        fprintf(fid,'%s\t%s\t%d\n',neuronName{MPIndices(i)},cType, difference(MPIndices(i)));
        fprintf(1,'%s\t%s\t%d\n',neuronName{MPIndices(i)},cType, difference(MPIndices(i)));
        
    end    
end
