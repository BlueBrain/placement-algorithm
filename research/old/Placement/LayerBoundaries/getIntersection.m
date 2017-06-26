function Coord= getIntersection (mOrth, m, bLayer, b)
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Returns intersection between layer and all orthogonal lines
% variables used under the form y-mx=b
% Coord obtained under the form= [y x]
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

A= [1 m;1 mOrth];
for i = 1: length (b) %loop through all orthogonal lines

D= [bLayer;b(i)];
Coord(i,:)= A\D;

end